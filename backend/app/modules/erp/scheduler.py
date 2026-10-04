# app/modules/erp/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from .models import ERPConnection

logger = logging.getLogger("erp.scheduler")
scheduler = BackgroundScheduler()

FREQUENCY_TRIGGERS = {
    "realtime": IntervalTrigger(minutes=15),   # 15 min mini pour ne pas spammer Odoo
    "hourly": CronTrigger(minute=0),
    "daily": CronTrigger(hour=2, minute=0),
}

MAX_RETRIES = 3


def _run_scheduled_sync(connection_id: str):
    """Exécuté par APScheduler dans un thread séparé — ouvre sa propre session DB."""
    from . import service  # import local pour éviter les cycles au chargement

    db: Session = SessionLocal()
    try:
        connection = db.query(ERPConnection).filter_by(id=connection_id).first()
        if not connection:
            logger.warning(f"Connexion ERP {connection_id} introuvable, job annulé.")
            unschedule_connection(connection_id)
            return

        attempt = 0
        log = None
        while attempt < MAX_RETRIES:
            attempt += 1
            log = service.run_sync(db, connection)
            if log.status == "success":
                logger.info(f"Sync {connection_id} réussie (tentative {attempt}).")
                return
            logger.warning(f"Sync {connection_id} échouée (tentative {attempt}/{MAX_RETRIES}) : {log.error_message}")

        # Toutes les tentatives ont échoué → connexion marquée en erreur persistante
        connection.status = "error"
        connection.last_error = f"Échec après {MAX_RETRIES} tentatives : {log.error_message if log else 'inconnu'}"
        db.commit()
        logger.error(f"Sync {connection_id} abandonnée après {MAX_RETRIES} tentatives.")

    finally:
        db.close()


def schedule_connection(connection_id: str, frequency: str):
    if frequency == "manual":
        unschedule_connection(connection_id)
        return
    trigger = FREQUENCY_TRIGGERS.get(frequency, FREQUENCY_TRIGGERS["daily"])
    scheduler.add_job(
        _run_scheduled_sync,
        trigger,
        args=[connection_id],
        id=f"erp-sync-{connection_id}",
        replace_existing=True,
        max_instances=1,  # évite qu'une sync lente en chevauche une autre
    )
    logger.info(f"Connexion {connection_id} planifiée : {frequency}")


def unschedule_connection(connection_id: str):
    job_id = f"erp-sync-{connection_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Connexion {connection_id} déplanifiée.")


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler ERP démarré.")


def load_existing_connections():
    """À appeler au démarrage de l'app pour replanifier les connexions déjà en base."""
    db: Session = SessionLocal()
    try:
        connections = db.query(ERPConnection).filter(
            ERPConnection.sync_frequency != "manual"
        ).all()
        for conn in connections:
            schedule_connection(conn.id, conn.sync_frequency)
        logger.info(f"{len(connections)} connexion(s) ERP replanifiée(s) au démarrage.")
    finally:
        db.close()