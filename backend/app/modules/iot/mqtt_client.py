"""
Client MQTT — app/modules/iot/mqtt_client.py
...
"""

import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import app.main  # noqa: F401 — force l'enregistrement de tous les modèles (companies, sites...) avant utilisation

import json
import logging

from aiomqtt import Client, MqttError

from app.core.database import SessionLocal
from app.modules.iot.schemas import ReadingIn
from app.modules.iot import service

logger = logging.getLogger("iot.mqtt_client")

MQTT_TOPIC_FILTER = "verdustry/+/reading"


async def _handle_message(topic: str, payload_bytes: bytes) -> None:
    try:
        data = json.loads(payload_bytes)
        reading_in = ReadingIn(**data)
    except Exception as exc:
        logger.warning("Payload MQTT invalide sur %s : %s", topic, exc)
        return

    with SessionLocal() as db:
        reading = service.ingest_reading(db, reading_in)
        if reading is None:
            logger.warning("device_uid inconnu reçu sur %s : %s", topic, reading_in.device_uid)
        else:
            logger.info("Mesure ingérée depuis MQTT : device=%s value=%s", reading_in.device_uid, reading_in.value)


async def run_mqtt_listener(host: str, port: int = 1883, username: str | None = None, password: str | None = None) -> None:
    """Boucle de connexion avec reconnexion automatique en cas de coupure."""
    while True:
        try:
            async with Client(hostname=host, port=port, username=username, password=password) as client:
                logger.info("Connecté au broker MQTT %s:%s", host, port)
                await client.subscribe(MQTT_TOPIC_FILTER)
                async for message in client.messages:
                    await _handle_message(str(message.topic), message.payload)
        except MqttError as error:
            logger.error("Erreur MQTT (%s) — reconnexion dans 5s", error)
            await asyncio.sleep(5)


if __name__ == "__main__":
    # Test rapide en local, ex. contre le broker public test.mosquitto.org :
    #   python -m app.modules.iot.mqtt_client
    logging.basicConfig(level=logging.INFO)
asyncio.run(run_mqtt_listener(host="broker.hivemq.com", port=1883))