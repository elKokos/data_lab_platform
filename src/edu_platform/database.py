from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import errors

RAW_SCHEMA_CREATE_SQL = """
CREATE SCHEMA raw AUTHORIZATION CURRENT_USER;
"""

RAW_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS raw.merchants_raw (
    batch_date date NOT NULL,
    merchant_ref text,
    merchant_name_raw text,
    merchant_country_raw text,
    contract_status_raw text,
    onboarding_channel_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.channels_raw (
    batch_date date NOT NULL,
    channel_code_raw text,
    channel_name_raw text,
    source_type_raw text,
    attribution_model_raw text,
    is_paid_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.devices_raw (
    batch_date date NOT NULL,
    device_code_raw text,
    device_family_raw text,
    os_name_raw text,
    app_version_raw text,
    browser_name_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.support_agents_raw (
    batch_date date NOT NULL,
    agent_ref text,
    full_name_raw text,
    team_name_raw text,
    region_raw text,
    shift_label_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.product_catalog_raw (
    batch_date date NOT NULL,
    product_ref text,
    merchant_ref text,
    sku_raw text,
    product_name_raw text,
    category_raw text,
    price_raw text,
    attributes_json jsonb,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.user_profiles_raw (
    batch_date date NOT NULL,
    user_ref text,
    registered_at_raw text,
    email_raw text,
    phone_raw text,
    city_raw text,
    country_raw text,
    acquisition_channel_raw text,
    preferences_json jsonb,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.sessions_raw (
    batch_date date NOT NULL,
    session_ref text,
    user_ref text,
    device_code_raw text,
    channel_code_raw text,
    started_at_raw text,
    ended_at_raw text,
    landing_page_raw text,
    ip_address_masked text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.app_events_raw (
    batch_date date NOT NULL,
    event_ref text,
    session_ref text,
    user_ref text,
    occurred_at_raw text,
    event_name_raw text,
    event_properties jsonb,
    ingestion_meta jsonb,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.orders_raw (
    batch_date date NOT NULL,
    order_ref text,
    user_ref text,
    session_ref text,
    merchant_ref text,
    created_at_raw text,
    order_status_raw text,
    total_amount_raw text,
    currency_raw text,
    promo_code_raw text,
    shipping_address_raw text,
    line_items_json jsonb,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.payment_attempts_raw (
    batch_date date NOT NULL,
    payment_ref text,
    order_ref text,
    attempted_at_raw text,
    payment_method_raw text,
    provider_raw text,
    payment_status_raw text,
    amount_raw text,
    error_message_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.refunds_raw (
    batch_date date NOT NULL,
    refund_ref text,
    order_ref text,
    payment_ref text,
    refunded_at_raw text,
    refund_status_raw text,
    refund_amount_raw text,
    refund_reason_raw text,
    raw_payload jsonb
);

CREATE TABLE IF NOT EXISTS raw.support_tickets_raw (
    batch_date date NOT NULL,
    ticket_ref text,
    user_ref text,
    order_ref text,
    agent_ref text,
    created_at_raw text,
    issue_type_raw text,
    status_raw text,
    priority_raw text,
    conversation_json jsonb,
    raw_payload jsonb
);

CREATE INDEX IF NOT EXISTS idx_merchants_raw_batch_date ON raw.merchants_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_channels_raw_batch_date ON raw.channels_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_devices_raw_batch_date ON raw.devices_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_support_agents_raw_batch_date ON raw.support_agents_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_product_catalog_raw_batch_date ON raw.product_catalog_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_user_profiles_raw_batch_date ON raw.user_profiles_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_sessions_raw_batch_date ON raw.sessions_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_app_events_raw_batch_date ON raw.app_events_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_orders_raw_batch_date ON raw.orders_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_payment_attempts_raw_batch_date ON raw.payment_attempts_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_refunds_raw_batch_date ON raw.refunds_raw (batch_date);
CREATE INDEX IF NOT EXISTS idx_support_tickets_raw_batch_date ON raw.support_tickets_raw (batch_date);
"""

RAW_SCHEMA_SQL = RAW_TABLES_SQL

TABLE_LOAD_ORDER = [
    "merchants_raw",
    "channels_raw",
    "devices_raw",
    "support_agents_raw",
    "product_catalog_raw",
    "user_profiles_raw",
    "sessions_raw",
    "app_events_raw",
    "orders_raw",
    "payment_attempts_raw",
    "refunds_raw",
    "support_tickets_raw",
]


def connection_kwargs() -> dict[str, str]:
    return {
        "host": os.environ["EDU_PLATFORM_DB_HOST"],
        "port": os.environ["EDU_PLATFORM_DB_PORT"],
        "dbname": os.environ["EDU_PLATFORM_DB"],
        "user": os.environ["EDU_PLATFORM_DB_USER"],
        "password": os.environ["EDU_PLATFORM_DB_PASSWORD"],
    }


@contextmanager
def get_connection():
    conn = psycopg2.connect(**connection_kwargs())
    try:
        yield conn
    finally:
        conn.close()


def ensure_raw_schema(cursor) -> None:
    cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'raw')")
    schema_exists = cursor.fetchone()[0]

    if not schema_exists:
        try:
            cursor.execute(RAW_SCHEMA_CREATE_SQL)
        except errors.InsufficientPrivilege as exc:
            raise RuntimeError(
                "Schema raw does not exist, and the current role cannot create it. "
                "Create schema raw once as postgres/platform_admin or grant CREATE ON DATABASE edu_platform."
            ) from exc

    cursor.execute(RAW_TABLES_SQL)
