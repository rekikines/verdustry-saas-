"""
Connecteur simulateur — app/modules/iot/connectors/simulator.py

Permet de développer et démontrer tout le pipeline (ingestion -> stockage
-> dashboard -> assistant IA) sans attendre le matériel du stage IoT.

Usage typique : une tâche de fond (scheduler.py ou script CLI) appelle
`run_simulation_tick(db)` toutes les N secondes pour tous les devices dont
`protocol == simulator`.
"""

import math
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.iot.models import IoTDevice, IoTProtocol
from app.modules.iot.schemas import ReadingIn
from app.modules.iot import service


def _simulate_value(device: IoTDevice, t: datetime) -> float:
    """Génère une valeur plausible selon le device_type, avec une variation
    temporelle (courbe de charge journalière, dérive lente) + bruit."""

    minute_of_day = t.hour * 60 + t.minute
    day_cycle = math.sin((minute_of_day / 1440) * 2 * math.pi)  # -1..1 sur 24h

    generators = {
        "energy_meter": lambda: max(0, 150 + 80 * day_cycle + random.gauss(0, 10)),       # kWh instantané
        "water_flow": lambda: max(0, 5 + 2 * day_cycle + random.gauss(0, 0.5)),            # m3/h
        "co2": lambda: max(350, 420 + 60 * max(day_cycle, 0) + random.gauss(0, 15)),       # ppm
        "pm25": lambda: max(0, 12 + 8 * max(day_cycle, 0) + random.gauss(0, 3)),           # µg/m3
        "waste_level": lambda: min(100, max(0, (minute_of_day / 1440) * 100 + random.gauss(0, 2))),  # % remplissage, monte sur la journée
        "weight": lambda: max(0, 200 + 50 * max(day_cycle, 0) + random.gauss(0, 5)),       # kg
    }

    generator = generators.get(device.device_type)
    if generator:
        return round(generator(), 2)

    # Type inconnu : valeur générique centrée sur 50
    return round(max(0, 50 + random.gauss(0, 10)), 2)


def run_simulation_tick(db: Session) -> int:
    """Génère et ingère une mesure pour chaque device simulé actif.
    Retourne le nombre de mesures ingérées."""

    stmt = select(IoTDevice).where(IoTDevice.protocol == IoTProtocol.simulator)
    devices = list(db.scalars(stmt))

    now = datetime.now(timezone.utc)
    count = 0
    for device in devices:
        value = _simulate_value(device, now)
        payload = ReadingIn(
            device_uid=device.device_uid,
            timestamp=now,
            value=value,
            raw_payload={"source": "simulator"},
        )
        if service.ingest_reading(db, payload) is not None:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Lancement autonome (hors scheduler) pour un test rapide en local :
#   python -m app.modules.iot.connectors.simulator
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time
    import app.main  # noqa: F401 — force l'enregistrement de tous les modèles (mappers) avant utilisation
    from app.core.database import SessionLocal

    print("Simulateur IoT démarré — Ctrl+C pour arrêter")
    while True:
        with SessionLocal() as db:
            n = run_simulation_tick(db)
            print(f"[{datetime.now().isoformat()}] {n} mesure(s) simulée(s) ingérée(s)")
        time.sleep(10)