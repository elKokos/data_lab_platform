from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

TABLE_COLUMNS: dict[str, list[str]] = {
    "merchants_raw": [
        "batch_date",
        "merchant_ref",
        "merchant_name_raw",
        "merchant_country_raw",
        "contract_status_raw",
        "onboarding_channel_raw",
        "raw_payload",
    ],
    "channels_raw": [
        "batch_date",
        "channel_code_raw",
        "channel_name_raw",
        "source_type_raw",
        "attribution_model_raw",
        "is_paid_raw",
        "raw_payload",
    ],
    "devices_raw": [
        "batch_date",
        "device_code_raw",
        "device_family_raw",
        "os_name_raw",
        "app_version_raw",
        "browser_name_raw",
        "raw_payload",
    ],
    "support_agents_raw": [
        "batch_date",
        "agent_ref",
        "full_name_raw",
        "team_name_raw",
        "region_raw",
        "shift_label_raw",
        "raw_payload",
    ],
    "product_catalog_raw": [
        "batch_date",
        "product_ref",
        "merchant_ref",
        "sku_raw",
        "product_name_raw",
        "category_raw",
        "price_raw",
        "attributes_json",
        "raw_payload",
    ],
    "user_profiles_raw": [
        "batch_date",
        "user_ref",
        "registered_at_raw",
        "email_raw",
        "phone_raw",
        "city_raw",
        "country_raw",
        "acquisition_channel_raw",
        "preferences_json",
        "raw_payload",
    ],
    "sessions_raw": [
        "batch_date",
        "session_ref",
        "user_ref",
        "device_code_raw",
        "channel_code_raw",
        "started_at_raw",
        "ended_at_raw",
        "landing_page_raw",
        "ip_address_masked",
        "raw_payload",
    ],
    "app_events_raw": [
        "batch_date",
        "event_ref",
        "session_ref",
        "user_ref",
        "occurred_at_raw",
        "event_name_raw",
        "event_properties",
        "ingestion_meta",
        "raw_payload",
    ],
    "orders_raw": [
        "batch_date",
        "order_ref",
        "user_ref",
        "session_ref",
        "merchant_ref",
        "created_at_raw",
        "order_status_raw",
        "total_amount_raw",
        "currency_raw",
        "promo_code_raw",
        "shipping_address_raw",
        "line_items_json",
        "raw_payload",
    ],
    "payment_attempts_raw": [
        "batch_date",
        "payment_ref",
        "order_ref",
        "attempted_at_raw",
        "payment_method_raw",
        "provider_raw",
        "payment_status_raw",
        "amount_raw",
        "error_message_raw",
        "raw_payload",
    ],
    "refunds_raw": [
        "batch_date",
        "refund_ref",
        "order_ref",
        "payment_ref",
        "refunded_at_raw",
        "refund_status_raw",
        "refund_amount_raw",
        "refund_reason_raw",
        "raw_payload",
    ],
    "support_tickets_raw": [
        "batch_date",
        "ticket_ref",
        "user_ref",
        "order_ref",
        "agent_ref",
        "created_at_raw",
        "issue_type_raw",
        "status_raw",
        "priority_raw",
        "conversation_json",
        "raw_payload",
    ],
}

COUNTRIES = [
    ("RU", ["Moscow", "Saint Petersburg", "Kazan", "Novosibirsk"]),
    ("KZ", ["Almaty", "Astana", "Shymkent"]),
    ("GE", ["Tbilisi", "Batumi", "Kutaisi"]),
    ("AM", ["Yerevan", "Gyumri", "Vanadzor"]),
    ("RS", ["Belgrade", "Novi Sad", "Nis"]),
    ("DE", ["Berlin", "Munich", "Hamburg"]),
]
CHANNEL_DEFS = [
    ("organic", "Organic Search", "web", "last_click"),
    ("paid_search", "Paid Search", "performance", "last_non_direct"),
    ("social", "Social Ads", "paid_social", "first_touch"),
    ("email", "CRM E-mail", "owned", "linear"),
    ("affiliate", "Affiliate Network", "partner", "last_click"),
    ("referral", "Referral", "partner", "last_click"),
]
DEVICE_DEFS = [
    ("mobile_ios", "mobile", "iOS", "16.7.2", "in_app"),
    ("mobile_android", "mobile", "Android", "14.0.1", "in_app"),
    ("desktop_chrome", "desktop", "Windows", "120.0.0", "Chrome"),
    ("desktop_safari", "desktop", "macOS", "17.1", "Safari"),
    ("tablet_ipad", "tablet", "iPadOS", "17.0", "in_app"),
]
AGENT_TEAMS = ["frontline", "payments", "returns", "logistics"]
ISSUE_TYPES = ["delivery_delay", "refund_question", "payment_issue", "damaged_item", "promo_problem"]
PROMO_CODES = ["SPRING10", "vip15", "WELCOME", "flash_25", "", ""]
MERCHANT_SEGMENTS = ["marketplace", "direct", "crossborder", "dropship"]
PRODUCT_CATEGORIES = ["electronics", "fashion", "beauty", "home", "grocery", "pet_care"]
EVENT_FLOW = ["app_open", "landing_view", "search", "product_view", "add_to_cart", "checkout_start", "payment_attempt", "purchase"]


@dataclass(frozen=True)
class DailyBatch:
    batch_date: date
    tables: dict[str, list[dict[str, Any]]]

    @property
    def counts(self) -> dict[str, int]:
        return {table_name: len(rows) for table_name, rows in self.tables.items()}


def build_daily_batch(batch_date: date) -> DailyBatch:
    rng = random.Random(20250628 + batch_date.toordinal())
    days_from_anchor = (batch_date - date(2025, 1, 1)).days
    seasonal = 1.0 + 0.25 * math.sin(days_from_anchor / 10)
    weekday_boost = 1.16 if batch_date.weekday() in (4, 5) else 0.9 if batch_date.weekday() == 0 else 1.0

    merchant_count = 35
    channel_count = len(CHANNEL_DEFS)
    device_count = len(DEVICE_DEFS)
    agent_count = 18
    user_count = max(180, int(220 + seasonal * 40 + rng.randint(-25, 30)))
    product_count = max(80, int(110 + seasonal * 20 + rng.randint(-15, 20)))
    session_count = max(1_600, int((2_100 + rng.randint(-180, 260)) * seasonal * weekday_boost))
    order_count = max(220, int(session_count * 0.17 + rng.randint(-20, 55)))

    user_pool = 40_000 + max(days_from_anchor, 0) * 60
    product_pool = 3_000 + max(days_from_anchor, 0) * 8
    batch_start = datetime.combine(batch_date, time(0, 0), tzinfo=timezone.utc)

    merchants = _generate_merchants(batch_date, merchant_count, rng)
    channels = _generate_channels(batch_date, rng)
    devices = _generate_devices(batch_date, rng)
    agents = _generate_support_agents(batch_date, agent_count, rng)
    products = _generate_products(batch_date, product_count, product_pool, merchants, rng)
    users = _generate_users(batch_date, user_count, user_pool, batch_start, rng)
    sessions = _generate_sessions(batch_date, session_count, user_pool, channels, devices, batch_start, rng)
    events = _generate_events(batch_date, sessions, products, batch_start, rng)
    orders = _generate_orders(batch_date, order_count, sessions, merchants, products, batch_start, rng)
    payments = _generate_payment_attempts(batch_date, orders, batch_start, rng)
    refunds = _generate_refunds(batch_date, orders, payments, rng)
    tickets = _generate_support_tickets(batch_date, orders, agents, batch_start, rng)

    return DailyBatch(
        batch_date=batch_date,
        tables={
            "merchants_raw": merchants,
            "channels_raw": channels,
            "devices_raw": devices,
            "support_agents_raw": agents,
            "product_catalog_raw": products,
            "user_profiles_raw": users,
            "sessions_raw": sessions,
            "app_events_raw": events,
            "orders_raw": orders,
            "payment_attempts_raw": payments,
            "refunds_raw": refunds,
            "support_tickets_raw": tickets,
        },
    )


def write_batch_to_csv(batch: DailyBatch, output_dir: str | Path) -> dict[str, Any]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    table_files: dict[str, str] = {}
    for table_name, rows in batch.tables.items():
        file_path = target_dir / f"{table_name}.csv"
        with file_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=TABLE_COLUMNS[table_name])
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        table_files[table_name] = str(file_path)

    return {
        "batch_date": batch.batch_date.isoformat(),
        "output_dir": str(target_dir),
        "table_files": table_files,
        "counts": batch.counts,
    }


def _generate_merchants(batch_date: date, count: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(1, count + 1):
        country_code, _ = rng.choice(COUNTRIES)
        segment = rng.choice(MERCHANT_SEGMENTS)
        merchant_name = f"{segment.title()} Shop {idx}"
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "merchant_ref": f"m_{idx:04d}",
                "merchant_name_raw": rng.choice([merchant_name, merchant_name.upper(), f" {merchant_name} "]),
                "merchant_country_raw": rng.choice([country_code, country_code.lower(), f"country={country_code}"]),
                "contract_status_raw": rng.choice(["active", "Active", "on_hold", "signed ", "pending_docs"]),
                "onboarding_channel_raw": rng.choice(["sales", "partner", "self_service", "referral"]),
                "raw_payload": _json(
                    {
                        "segment": segment,
                        "external_rating": round(rng.uniform(3.1, 4.9), 2),
                        "contact": {"email": f"merchant{idx}@example.com", "telegram": f"@merchant_{idx}"},
                    }
                ),
            }
        )
    return rows


def _generate_channels(batch_date: date, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code, name, source_type, attribution in CHANNEL_DEFS:
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "channel_code_raw": rng.choice([code, code.upper(), code.replace("_", "-")]),
                "channel_name_raw": rng.choice([name, name.lower(), f"{name} "]),
                "source_type_raw": source_type,
                "attribution_model_raw": rng.choice([attribution, attribution.upper(), attribution.replace("_", "-")]),
                "is_paid_raw": rng.choice(["true", "false", "Y", "N", "1", "0"]),
                "raw_payload": _json({"utm_source": code, "owner_team": rng.choice(["growth", "crm", "brand"])}),
            }
        )
    return rows


def _generate_devices(batch_date: date, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code, family, os_name, version, browser in DEVICE_DEFS:
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "device_code_raw": rng.choice([code, code.upper()]),
                "device_family_raw": rng.choice([family, family.title(), f"{family}_device"]),
                "os_name_raw": rng.choice([os_name, os_name.lower(), f"{os_name} OS"]),
                "app_version_raw": rng.choice([version, f"v{version}", version.replace(".", "_")]),
                "browser_name_raw": browser,
                "raw_payload": _json({"sdk": rng.choice(["flutter", "react_native", "web_js"]), "screen": rng.choice(["1080x1920", "1440x900", "834x1194"])}),
            }
        )
    return rows


def _generate_support_agents(batch_date: date, count: int, rng: random.Random) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(1, count + 1):
        team = rng.choice(AGENT_TEAMS)
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "agent_ref": f"agt_{idx:03d}",
                "full_name_raw": rng.choice([f"Agent {idx}", f"agent_{idx}", f"Support Agent {idx}"]),
                "team_name_raw": rng.choice([team, team.upper(), f"{team}_team"]),
                "region_raw": rng.choice(["emea", "cis", "remote"]),
                "shift_label_raw": rng.choice(["day", "night", "swing", "night_shift"]),
                "raw_payload": _json({"language_skills": rng.sample(["ru", "en", "de", "ka"], k=rng.randint(1, 3))}),
            }
        )
    return rows


def _generate_products(
    batch_date: date,
    count: int,
    product_pool: int,
    merchants: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    merchant_refs = [row["merchant_ref"] for row in merchants]
    start_product_id = product_pool - count + 1
    for offset in range(count):
        product_ref = f"prd_{start_product_id + offset:06d}"
        category = rng.choice(PRODUCT_CATEGORIES)
        price = round(rng.uniform(5.5, 450.0), 2)
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "product_ref": product_ref,
                "merchant_ref": rng.choice(merchant_refs),
                "sku_raw": rng.choice([f"SKU-{product_ref[-6:]}", f"sku_{product_ref[-6:]}", f"{product_ref[-6:]}"]),
                "product_name_raw": rng.choice(
                    [
                        f"{category.title()} Item {offset + 1}",
                        f"{category}_{offset + 1}",
                        f" {category.title()} / item {offset + 1} ",
                    ]
                ),
                "category_raw": rng.choice([category, category.upper(), category.replace("_", " ")]),
                "price_raw": _dirty_amount(price, rng.choice(["USD", "EUR", "RUB"]), rng),
                "attributes_json": _json(
                    {
                        "color": rng.choice(["black", "white", "green", None]),
                        "size": rng.choice(["S", "M", "L", None]),
                        "fragile": rng.choice([True, False, False]),
                    }
                ),
                "raw_payload": _json({"source_file": f"catalog_{batch_date:%Y%m%d}.json", "warehouse_cnt": rng.randint(1, 5)}),
            }
        )
    return rows


def _generate_users(
    batch_date: date,
    count: int,
    user_pool: int,
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start_user_id = user_pool - count + 1
    for offset in range(count):
        country_code, cities = rng.choice(COUNTRIES)
        created_at = batch_start - timedelta(days=rng.randint(0, 700), minutes=rng.randint(0, 1440))
        user_ref = f"usr_{start_user_id + offset:07d}"
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "user_ref": user_ref,
                "registered_at_raw": _dirty_timestamp(created_at, rng),
                "email_raw": rng.choice([f"{user_ref}@example.com", f"{user_ref}@mail.ru", "", f" {user_ref}@test.local "]),
                "phone_raw": rng.choice([f"+7-900-{rng.randint(100,999)}-{rng.randint(10,99)}-{rng.randint(10,99)}", "", "unknown", f"79{rng.randint(10**8, 10**9 - 1)}"]),
                "city_raw": rng.choice([rng.choice(cities), rng.choice(cities).upper(), "", f"city:{rng.choice(cities)}"]),
                "country_raw": rng.choice([country_code, country_code.lower(), f"country={country_code}", ""]),
                "acquisition_channel_raw": rng.choice(["organic", "paid-search", "social_ads", "Email", "referral"]),
                "preferences_json": _json({"marketing_opt_in": rng.choice(["true", "false", None]), "language": rng.choice(["ru", "en", "de"])}),
                "raw_payload": _json({"tags": rng.sample(["vip", "refund_risk", "new", "b2b"], k=rng.randint(0, 2)), "profile_quality": rng.choice(["full", "partial", "broken"])}),
            }
        )
    return rows


def _generate_sessions(
    batch_date: date,
    count: int,
    user_pool: int,
    channels: list[dict[str, Any]],
    devices: list[dict[str, Any]],
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    channel_codes = [row["channel_code_raw"] for row in channels]
    device_codes = [row["device_code_raw"] for row in devices]
    for idx in range(count):
        started_at = batch_start + timedelta(minutes=rng.randint(0, 1439), seconds=rng.randint(0, 59))
        ended_at = started_at + timedelta(seconds=rng.randint(45, 5_400))
        user_ref = f"usr_{rng.randint(1, user_pool):07d}"
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "session_ref": f"sess_{batch_date:%Y%m%d}_{idx:06d}",
                "user_ref": user_ref,
                "device_code_raw": rng.choice(device_codes),
                "channel_code_raw": rng.choice(channel_codes),
                "started_at_raw": _dirty_timestamp(started_at, rng),
                "ended_at_raw": _dirty_timestamp(ended_at, rng),
                "landing_page_raw": rng.choice(["/", "/catalog", "/promo/summer", "/search?q=phone", "/checkout"]),
                "ip_address_masked": f"10.{rng.randint(0,255)}.x.{rng.randint(0,255)}",
                "raw_payload": _json({"utm_campaign": rng.choice(["brand", "retargeting", None]), "ab_bucket": rng.choice(["A", "B", "control"])}),
            }
        )
    return rows


def _generate_events(
    batch_date: date,
    sessions: list[dict[str, Any]],
    products: list[dict[str, Any]],
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    del batch_start
    rows: list[dict[str, Any]] = []
    product_refs = [row["product_ref"] for row in products]
    for session in sessions:
        event_count = rng.randint(4, 8)
        event_time = _parse_rough_timestamp(session["started_at_raw"])
        for idx in range(event_count):
            event_name = EVENT_FLOW[min(idx, len(EVENT_FLOW) - 1)]
            event_time = event_time + timedelta(seconds=rng.randint(10, 180))
            late_hours = 24 if rng.random() < 0.03 else 0
            properties = {
                "page": rng.choice(["home", "catalog", "search", "product", "cart", "checkout"]),
                "product_ref": rng.choice(product_refs) if event_name in {"product_view", "add_to_cart"} else None,
                "position": rng.choice([1, 2, 3, None]),
            }
            rows.append(
                {
                    "batch_date": batch_date.isoformat(),
                    "event_ref": f"evt_{session['session_ref']}_{idx + 1}",
                    "session_ref": session["session_ref"],
                    "user_ref": session["user_ref"],
                    "occurred_at_raw": _dirty_timestamp(event_time, rng),
                    "event_name_raw": rng.choice([event_name, event_name.upper(), event_name.replace("_", "-")]),
                    "event_properties": _json(properties),
                    "ingestion_meta": _json({"received_at": _dirty_timestamp(event_time + timedelta(minutes=rng.randint(0, 9), hours=late_hours), rng), "is_late": late_hours > 0}),
                    "raw_payload": _json({"source": "mobile_sdk", "tracking_version": rng.choice(["1.0", "1.1", "legacy"])}),
                }
            )
            if rng.random() < 0.015:
                duplicate = dict(rows[-1])
                duplicate["event_ref"] = f"{duplicate['event_ref']}_dup"
                duplicate["raw_payload"] = _json({"source": "replay", "duplicate_of": rows[-1]["event_ref"]})
                rows.append(duplicate)
    return rows


def _generate_orders(
    batch_date: date,
    count: int,
    sessions: list[dict[str, Any]],
    merchants: list[dict[str, Any]],
    products: list[dict[str, Any]],
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    del batch_start
    rows: list[dict[str, Any]] = []
    merchant_refs = [row["merchant_ref"] for row in merchants]
    product_refs = [row["product_ref"] for row in products]
    chosen_sessions = rng.sample(sessions, k=min(count, len(sessions)))
    for idx in range(count):
        session = chosen_sessions[idx % len(chosen_sessions)]
        created_at = _parse_rough_timestamp(session["started_at_raw"]) + timedelta(minutes=rng.randint(2, 120))
        item_count = rng.randint(1, 4)
        line_items: list[dict[str, Any]] = []
        total_amount = 0.0
        for item_idx in range(item_count):
            unit_price = round(rng.uniform(7.0, 180.0), 2)
            quantity = rng.randint(1, 3)
            total_amount += unit_price * quantity
            line_items.append(
                {
                    "line_num": item_idx + 1,
                    "product_ref": rng.choice(product_refs),
                    "qty": rng.choice([str(quantity), quantity]),
                    "unit_price": rng.choice([str(unit_price), f"{unit_price:.2f}", f"USD {unit_price:.2f}"]),
                    "discount": rng.choice(["0", "0.00", "", "5%", None]),
                }
            )

        order_ref = f"ord_{batch_date:%Y%m%d}_{idx:05d}"
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "order_ref": order_ref,
                "user_ref": session["user_ref"],
                "session_ref": session["session_ref"],
                "merchant_ref": rng.choice(merchant_refs),
                "created_at_raw": _dirty_timestamp(created_at, rng),
                "order_status_raw": rng.choice(["paid", "PAID", "pending", "cancelled", "refund_requested", "paid "]),
                "total_amount_raw": _dirty_amount(total_amount, rng.choice(["USD", "EUR", "RUB"]), rng),
                "currency_raw": rng.choice(["USD", "usd", "EUR", "RUB", "RUR"]),
                "promo_code_raw": rng.choice(PROMO_CODES),
                "shipping_address_raw": rng.choice(
                    [
                        "Moscow; Tverskaya 1; apt 5",
                        "Berlin, Main str. 3",
                        "Almaty | Dostyk 10",
                        "",
                    ]
                ),
                "line_items_json": _json(line_items),
                "raw_payload": _json({"checkout_source": rng.choice(["web", "app", "call_center"]), "fraud_score": round(rng.uniform(0.02, 0.88), 2)}),
            }
        )
    return rows


def _generate_payment_attempts(
    batch_date: date,
    orders: list[dict[str, Any]],
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    del batch_start
    rows: list[dict[str, Any]] = []
    for order in orders:
        attempt_count = 2 if rng.random() < 0.14 else 1
        order_created_at = _parse_rough_timestamp(order["created_at_raw"])
        for attempt_idx in range(attempt_count):
            status = rng.choice(["captured", "captured", "failed", "pending_review"])
            error_message = ""
            if status == "failed":
                error_message = rng.choice(["bank_timeout", "3ds_failed", "insufficient_funds", "risk_decline"])
            rows.append(
                {
                    "batch_date": batch_date.isoformat(),
                    "payment_ref": f"pay_{order['order_ref']}_{attempt_idx + 1}",
                    "order_ref": order["order_ref"],
                    "attempted_at_raw": _dirty_timestamp(order_created_at + timedelta(minutes=attempt_idx * rng.randint(1, 15) + 5), rng),
                    "payment_method_raw": rng.choice(["card", "CARD", "apple-pay", "sbp", "paypal"]),
                    "provider_raw": rng.choice(["stripe", "Stripe", "yookassa", "bank_gateway"]),
                    "payment_status_raw": status,
                    "amount_raw": order["total_amount_raw"],
                    "error_message_raw": error_message,
                    "raw_payload": _json({"installments": rng.choice([1, 1, 3, 6]), "attempt_no": attempt_idx + 1}),
                }
            )
    return rows


def _generate_refunds(
    batch_date: date,
    orders: list[dict[str, Any]],
    payments: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payments_by_order: dict[str, list[dict[str, Any]]] = {}
    for payment in payments:
        payments_by_order.setdefault(payment["order_ref"], []).append(payment)

    for order in orders:
        if "refund" not in str(order["order_status_raw"]).lower() and rng.random() > 0.06:
            continue
        related_payment = rng.choice(payments_by_order[order["order_ref"]])
        refund_time = _parse_rough_timestamp(order["created_at_raw"]) + timedelta(hours=rng.randint(12, 96))
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "refund_ref": f"rfd_{order['order_ref']}",
                "order_ref": order["order_ref"],
                "payment_ref": related_payment["payment_ref"],
                "refunded_at_raw": _dirty_timestamp(refund_time, rng),
                "refund_status_raw": rng.choice(["approved", "APPROVED", "pending", "rejected"]),
                "refund_amount_raw": rng.choice([order["total_amount_raw"], "", "partial", "49,90"]),
                "refund_reason_raw": rng.choice(["customer_changed_mind", "damaged_item", "delivery_issue", "fraud"]),
                "raw_payload": _json({"initiated_by": rng.choice(["customer", "support", "risk_system"]), "sla_hours": rng.randint(4, 72)}),
            }
        )
    return rows


def _generate_support_tickets(
    batch_date: date,
    orders: list[dict[str, Any]],
    agents: list[dict[str, Any]],
    batch_start: datetime,
    rng: random.Random,
) -> list[dict[str, Any]]:
    del batch_start
    rows: list[dict[str, Any]] = []
    agent_refs = [row["agent_ref"] for row in agents]
    for order in orders:
        if rng.random() > 0.12 and "cancel" not in str(order["order_status_raw"]).lower():
            continue
        created_at = _parse_rough_timestamp(order["created_at_raw"]) + timedelta(hours=rng.randint(1, 72))
        conversation = [
            {"speaker": "customer", "text": rng.choice(["where is my order?", "payment failed again", "need refund", "wrong item"])},
            {"speaker": "agent", "text": rng.choice(["checking now", "please wait", "refund initiated", "need more details"])},
        ]
        rows.append(
            {
                "batch_date": batch_date.isoformat(),
                "ticket_ref": f"tkt_{order['order_ref']}",
                "user_ref": order["user_ref"],
                "order_ref": order["order_ref"],
                "agent_ref": rng.choice(agent_refs),
                "created_at_raw": _dirty_timestamp(created_at, rng),
                "issue_type_raw": rng.choice(ISSUE_TYPES),
                "status_raw": rng.choice(["open", "resolved", "waiting_customer", "closed", "Open"]),
                "priority_raw": rng.choice(["low", "medium", "high", "urgent"]),
                "conversation_json": _json(conversation),
                "raw_payload": _json({"first_response_minutes": rng.choice([5, 12, 64, None]), "csat_raw": rng.choice(["5", "4", "", None])}),
            }
        )
    return rows


def _dirty_timestamp(dt: datetime, rng: random.Random) -> str:
    formats = [
        dt.isoformat(),
        dt.strftime("%Y-%m-%d %H:%M:%S"),
        dt.strftime("%d-%m-%Y %H:%M"),
        dt.strftime("%Y/%m/%d %H:%M:%S"),
        dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    ]
    return rng.choice(formats + ([""] if rng.random() < 0.02 else []))


def _parse_rough_timestamp(value: str) -> datetime:
    for parser in (
        lambda raw: datetime.fromisoformat(raw.replace("Z", "+00:00")),
        lambda raw: datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc),
        lambda raw: datetime.strptime(raw, "%d-%m-%Y %H:%M").replace(tzinfo=timezone.utc),
        lambda raw: datetime.strptime(raw, "%Y/%m/%d %H:%M:%S").replace(tzinfo=timezone.utc),
    ):
        try:
            parsed = parser(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return datetime(2026, 1, 1, tzinfo=timezone.utc)


def _dirty_amount(amount: float, currency: str, rng: random.Random) -> str:
    normalized = f"{amount:.2f}"
    return rng.choice(
        [
            normalized,
            normalized.replace(".", ","),
            f"{currency} {normalized}",
            f"{normalized} {currency}",
            f"amount={normalized}",
            "",
        ]
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)

