from __future__ import annotations

from edu_platform.database import RAW_SCHEMA_SQL, get_connection


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(RAW_SCHEMA_SQL)
        conn.commit()
    print("Initialized raw schema in edu_platform.")


if __name__ == "__main__":
    main()
