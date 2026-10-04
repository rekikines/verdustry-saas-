"""
Scheduler — app/modules/iot/scheduler.py

Même pattern que le scheduler déjà présent dans erp/. Deux jobs :
- flag_offline_devices_job  : détecte les capteurs qui n'émettent plus
- simulation_tick_job       : fait avancer les capteurs simulés (dev/démo)

Branchement (dans votre configuration APScheduler existante, main.py ou
équivalent) :

    from app.modules.iot.scheduler import register_iot_jobs
    register_iot_jobs(scheduler)
"""

import logging
from app.core.database import SessionLocal
from app.modules.iot import service
from app.modules.iot.connectors.simulator import run_simulation_tick

logger = logging.getLogger("iot.scheduler")


def flag_offline_devices_job(offline_after_minutes: int = 30) -> None:
    with SessionLocal() as db:
        alerts = service.flag_offline_devices(db, offline_after_minutes=offline_after_minutes)
        if alerts:
            logger.info("%d capteur(s) marqué(s) hors ligne", len(alerts))


def simulation_tick_job() -> None:
    with SessionLocal() as db:
        n = run_simulation_tick(db)
        if n:
            logger.debug("%d mesure(s) simulée(s) ingérée(s)", n)


def register_iot_jobs(scheduler) -> None:
    """À appeler une fois au démarrage de l'application avec votre instance
    APScheduler existante (BackgroundScheduler ou AsyncIOScheduler)."""
    scheduler.add_job(flag_offline_devices_job, "interval", minutes=5, id="iot_flag_offline_devices")
    scheduler.add_job(simulation_tick_job, "interval", seconds=10, id="iot_simulation_tick")
