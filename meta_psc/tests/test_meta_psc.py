from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


review_analyzer = load_script("review_analyzer")
trajectory_summary = load_script("trajectory_summary")


class ReviewAnalyzerTests(unittest.TestCase):
    def test_psc_cycle_mapping(self):
        self.assertEqual(review_analyzer.map_period("Q1 2024 PSC", "", None), "2023 H2")
        self.assertEqual(review_analyzer.map_period("Q3 2024 PSC", "", None), "2024 H1")
        self.assertEqual(review_analyzer.map_period("2024 Year-end", "", None), "2024 H2")
        self.assertEqual(review_analyzer.map_period("2024 Mid-year", "", None), "2024 H1")

    def test_rating_extraction_uses_generic_name(self):
        rating, evidence = review_analyzer.parse_rating("Rating for Example Person is greatly exceeded expectations")
        self.assertEqual(rating, "Greatly Exceeds Expectations")
        self.assertIn("Example Person", evidence)

    def test_level_and_promo_extraction(self):
        text = "First half as E6 after being transitioned from M1 to SWE. Later promoted to IC7."
        self.assertEqual(review_analyzer.parse_explicit_levels(text), ["E6", "IC7", "M1"])
        self.assertEqual(
            review_analyzer.parse_promos(text),
            ["promoted to IC7", "transitioned from M1 to SWE", "First half as E6"],
        )

    def test_write_csv_includes_headers_for_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reviews_analysis.csv"
            review_analyzer.write_csv(path, [])
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows, [review_analyzer.CSV_FIELDS])


class TrajectorySummaryTests(unittest.TestCase):
    def test_level_bucket_tracks(self):
        self.assertEqual(trajectory_summary.level_bucket("IC6"), "IC")
        self.assertEqual(trajectory_summary.level_bucket("E7"), "IC")
        self.assertEqual(trajectory_summary.level_bucket("M1"), "Manager")
        self.assertEqual(trajectory_summary.level_bucket("Engineer (inferred from role)"), "Unknown")

    def test_duplicate_period_prefers_explicit_rating(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reviews_analysis.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=review_analyzer.CSV_FIELDS)
                writer.writeheader()
                writer.writerow(
                    {
                        "file": "draft.pdf",
                        "submitted": "2024-08-01",
                        "cycle_label": "Q3 2024 PSC",
                        "period": "2024 H1",
                        "rating": "",
                        "rating_evidence": "",
                        "role": "",
                        "explicit_levels": "",
                        "inferred_level": "E6",
                        "promos": "",
                    }
                )
                writer.writerow(
                    {
                        "file": "final.pdf",
                        "submitted": "2024-08-02",
                        "cycle_label": "Q3 2024 PSC",
                        "period": "2024 H1",
                        "rating": "Exceeds Expectations",
                        "rating_evidence": "rating",
                        "role": "",
                        "explicit_levels": "",
                        "inferred_level": "E6",
                        "promos": "",
                    }
                )
            rows = trajectory_summary.read_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].file, "final.pdf")
        self.assertEqual(rows[0].rating, "Exceeds Expectations")


if __name__ == "__main__":
    unittest.main()
