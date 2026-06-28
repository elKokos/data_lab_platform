from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from edu_platform.data_generator import TABLE_COLUMNS, build_daily_batch


class DataGeneratorTests(unittest.TestCase):
    def test_build_daily_batch_has_all_expected_tables(self):
        batch = build_daily_batch(date(2026, 6, 1))

        self.assertEqual(set(batch.tables.keys()), set(TABLE_COLUMNS.keys()))
        self.assertGreater(batch.counts["app_events_raw"], batch.counts["sessions_raw"])
        self.assertGreater(batch.counts["orders_raw"], 100)

    def test_generated_references_are_present(self):
        batch = build_daily_batch(date(2026, 6, 1))

        session_refs = {row["session_ref"] for row in batch.tables["sessions_raw"]}
        order_refs = {row["order_ref"] for row in batch.tables["orders_raw"]}
        merchant_refs = {row["merchant_ref"] for row in batch.tables["merchants_raw"]}

        for event in batch.tables["app_events_raw"]:
            self.assertIn(event["session_ref"], session_refs)

        for order in batch.tables["orders_raw"]:
            self.assertIn(order["session_ref"], session_refs)
            self.assertIn(order["merchant_ref"], merchant_refs)

    def test_raw_layer_contains_json_payloads_and_dirty_strings(self):
        batch = build_daily_batch(date(2026, 6, 1))

        sample_order = batch.tables["orders_raw"][0]
        sample_event = batch.tables["app_events_raw"][0]
        sample_user = batch.tables["user_profiles_raw"][0]

        self.assertTrue(sample_order["line_items_json"].startswith("["))
        self.assertTrue(sample_event["event_properties"].startswith("{"))
        self.assertTrue(sample_user["raw_payload"].startswith("{"))
        self.assertIsInstance(sample_order["total_amount_raw"], str)

    def test_generation_is_deterministic_per_day(self):
        left = build_daily_batch(date(2026, 6, 2))
        right = build_daily_batch(date(2026, 6, 2))

        self.assertEqual(left.counts, right.counts)
        self.assertEqual(left.tables["orders_raw"][:5], right.tables["orders_raw"][:5])

if __name__ == "__main__":
    unittest.main()
