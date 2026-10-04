# create_iot_tables.py
from app.core.database import Base, engine

# companies ET sites sont tous les deux dans auth/models.py
import app.modules.auth.models
import app.modules.sources.models   # data_sources

from app.modules.iot import models as iot_models

Base.metadata.create_all(bind=engine, tables=[
    iot_models.IoTGateway.__table__,
    iot_models.IoTDevice.__table__,
    iot_models.IoTReading.__table__,
    iot_models.IoTAlert.__table__,
])
print("Tables IoT créées.")