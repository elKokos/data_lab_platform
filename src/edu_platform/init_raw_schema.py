from __future__ import annotations

from edu_platform.database import ensure_raw_schema, get_connection


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            ensure_raw_schema(cursor)
        conn.commit()
    print("Initialized raw schema in edu_platform.")


if __name__ == "__main__":
    main()
