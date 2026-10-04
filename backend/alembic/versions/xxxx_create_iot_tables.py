"""create iot tables

Revision ID: xxxx_create_iot_tables
Revises: <mettre_ici_la_derniere_revision_existante>
Create Date: 2026-08-25

Renommez ce fichier avec un vrai identifiant de révision Alembic
(ou laissez `alembic revision --autogenerate` le régénérer une fois
models.py importé dans env.py), et fixez `down_revision`.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "xxxx_create_iot_tables"
down_revision = "<mettre_ici_la_derniere_revision_existante>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    iot_protocol = postgresql.ENUM("modbus_rtu", "modbus_tcp", "mqtt", "lorawan", "http", "simulator", name="iot_protocol")
    iot_category = postgresql.ENUM("energie", "eau", "dechets", "emissions", "ambiance", name="iot_category")
    iot_device_status = postgresql.ENUM("active", "inactive", "error", name="iot_device_status")
    iot_gateway_status = postgresql.ENUM("online", "offline", "degraded", name="iot_gateway_status")
    iot_quality_flag = postgresql.ENUM("ok", "out_of_range", "duplicate", "gap_filled", name="iot_quality_flag")
    iot_alert_type = postgresql.ENUM("offline", "out_of_range", "threshold_exceeded", name="iot_alert_type")

    bind = op.get_bind()
    for enum_type in (iot_protocol, iot_category, iot_device_status, iot_gateway_status, iot_quality_flag, iot_alert_type):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "iot_gateways",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("company_id", sa.String(40), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(40), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", iot_gateway_status, nullable=False, server_default="offline"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_iot_gateways_company_id", "iot_gateways", ["company_id"])
    op.create_index("ix_iot_gateways_site_id", "iot_gateways", ["site_id"])
    op.create_index("ix_iot_gateways_company_site", "iot_gateways", ["company_id", "site_id"])

    op.create_table(
        "iot_devices",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("company_id", sa.String(40), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(40), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data_source_id", sa.String(40), sa.ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gateway_id", sa.String(40), sa.ForeignKey("iot_gateways.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_uid", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(100), nullable=False),
        sa.Column("category", iot_category, nullable=False),
        sa.Column("protocol", iot_protocol, nullable=False),
        sa.Column("connection_params", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("min_valid_value", sa.Float, nullable=True),
        sa.Column("max_valid_value", sa.Float, nullable=True),
        sa.Column("alert_threshold", sa.Float, nullable=True),
        sa.Column("status", iot_device_status, nullable=False, server_default="active"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_iot_devices_company_id", "iot_devices", ["company_id"])
    op.create_index("ix_iot_devices_site_id", "iot_devices", ["site_id"])
    op.create_index("ix_iot_devices_company_site", "iot_devices", ["company_id", "site_id"])
    op.create_index("ix_iot_devices_data_source_id", "iot_devices", ["data_source_id"])
    op.create_index("ix_iot_devices_gateway_id", "iot_devices", ["gateway_id"])

    op.create_table(
        "iot_readings",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("company_id", sa.String(40), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(40), sa.ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("quality_flag", iot_quality_flag, nullable=False, server_default="ok"),
    )
    op.create_index("ix_iot_readings_company_id", "iot_readings", ["company_id"])
    op.create_index("ix_iot_readings_device_id", "iot_readings", ["device_id"])
    op.create_index("ix_iot_readings_timestamp", "iot_readings", ["timestamp"])
    op.create_index("ix_iot_readings_device_timestamp", "iot_readings", ["device_id", "timestamp"])

    op.create_table(
        "iot_alerts",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("company_id", sa.String(40), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(40), sa.ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", iot_alert_type, nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_iot_alerts_company_id", "iot_alerts", ["company_id"])
    op.create_index("ix_iot_alerts_device_id", "iot_alerts", ["device_id"])

    # Optionnel : TimescaleDB sur iot_readings
    # op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    # op.execute("SELECT create_hypertable('iot_readings', 'timestamp', if_not_exists => TRUE);")


def downgrade() -> None:
    op.drop_table("iot_alerts")
    op.drop_table("iot_readings")
    op.drop_table("iot_devices")
    op.drop_table("iot_gateways")
    for enum_name in ("iot_alert_type", "iot_quality_flag", "iot_gateway_status", "iot_device_status", "iot_category", "iot_protocol"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
