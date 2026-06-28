from __future__ import annotations

import os
import shutil
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.decorators import dag, get_current_context, task

from edu_platform.data_generator import build_daily_batch, write_batch_to_csv
from edu_platform.database import RAW_SCHEMA_SQL, TABLE_LOAD_ORDER, get_connection


def _batch_date_from_context() -> str:
    context = get_current_context()
    return context["ds"]


@dag(
    dag_id="generate_daily_training_data",
    start_date=pendulum.parse(os.getenv("AIRFLOW_DAG_START_DATE", "2025-12-30")),
    schedule="@daily",
    catchup=True,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=2),
    default_args={"owner": "platform_admin", "retries": 1, "retry_delay": timedelta(minutes=10)},
    tags=["education", "postgres", "synthetic-data"],
)
def generate_daily_training_data():
    @task
    def ensure_raw_schema() -> None:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(RAW_SCHEMA_SQL)
            conn.commit()

    @task
    def generate_batch_files() -> dict[str, object]:
        batch_date = pendulum.parse(_batch_date_from_context()).date()
        batch = build_daily_batch(batch_date)
        output_root = Path(os.getenv("AIRFLOW_TMP_DIR", "/opt/airflow/tmp"))
        return write_batch_to_csv(batch, output_root / batch_date.isoformat())

    @task
    def load_to_raw(manifest: dict[str, object]) -> dict[str, int]:
        batch_date = manifest["batch_date"]
        table_files = manifest["table_files"]
        counts = manifest["counts"]

        with get_connection() as conn:
            with conn.cursor() as cursor:
                for table_name in reversed(TABLE_LOAD_ORDER):
                    cursor.execute(f"DELETE FROM raw.{table_name} WHERE batch_date = %s", (batch_date,))

                for table_name in TABLE_LOAD_ORDER:
                    file_path = table_files[table_name]
                    with open(file_path, "r", encoding="utf-8") as csv_file:
                        cursor.copy_expert(
                            f"""
                            COPY raw.{table_name}
                            FROM STDIN
                            WITH (FORMAT csv, HEADER true)
                            """,
                            csv_file,
                        )
            conn.commit()
        return counts

    @task
    def run_quality_checks(expected_counts: dict[str, int]) -> None:
        batch_date = _batch_date_from_context()
        with get_connection() as conn:
            with conn.cursor() as cursor:
                for table_name, expected_count in expected_counts.items():
                    cursor.execute(f"SELECT COUNT(*) FROM raw.{table_name} WHERE batch_date = %s", (batch_date,))
                    actual_count = cursor.fetchone()[0]
                    if actual_count != expected_count:
                        raise ValueError(
                            f"Count mismatch for {table_name}: expected {expected_count}, got {actual_count}"
                        )

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM raw.orders_raw o
                    WHERE o.batch_date = %s
                      AND (
                        jsonb_typeof(o.line_items_json) <> 'array'
                        OR jsonb_array_length(o.line_items_json) = 0
                      )
                    """,
                    (batch_date,),
                )
                broken_orders = cursor.fetchone()[0]
                if broken_orders:
                    raise ValueError("At least one order was loaded without line items JSON.")

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM raw.payment_attempts_raw
                    WHERE batch_date = %s
                      AND lower(payment_status_raw) = 'failed'
                      AND coalesce(trim(error_message_raw), '') = ''
                    """,
                    (batch_date,),
                )
                failed_without_reason = cursor.fetchone()[0]
                if failed_without_reason:
                    raise ValueError("Failed payments must include a failure reason.")

                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM raw.app_events_raw e
                    LEFT JOIN raw.sessions_raw s
                      ON s.session_ref = e.session_ref
                     AND s.batch_date = e.batch_date
                    WHERE e.batch_date = %s
                      AND s.session_ref IS NULL
                    """,
                    (batch_date,),
                )
                events_without_session = cursor.fetchone()[0]
                if events_without_session:
                    raise ValueError("At least one event was loaded without a matching session.")

    @task(trigger_rule="all_done")
    def cleanup_temp_files(manifest: dict[str, object]) -> None:
        output_dir = manifest["output_dir"]
        if output_dir and Path(output_dir).exists():
            shutil.rmtree(output_dir, ignore_errors=True)

    schema_ready = ensure_raw_schema()
    manifest = generate_batch_files()
    loaded_counts = load_to_raw(manifest)
    checks = run_quality_checks(loaded_counts)
    schema_ready >> manifest
    checks >> cleanup_temp_files(manifest)


generate_daily_training_data()
