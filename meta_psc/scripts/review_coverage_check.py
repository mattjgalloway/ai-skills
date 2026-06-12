#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import List, Set


def parse_period(period: str):
    m = re.match(r"(\d{4})\s+H([12])", period or "")
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def ask_int(prompt: str, default: int | None = None) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        if raw.isdigit():
            return int(raw)
        print("Please enter a number.")


def expected_periods(start_year: int, start_half: int, end_year: int, end_half: int) -> List[str]:
    periods = []
    y, h = start_year, start_half
    while (y, h) <= (end_year, end_half):
        periods.append(f"{y} H{h}")
        if h == 1:
            h = 2
        else:
            y += 1
            h = 1
    return periods


def main() -> None:
    ap = argparse.ArgumentParser(description="Check missing review periods from analysis CSV")
    ap.add_argument("--input-csv", default="output/reviews_analysis.csv")
    ap.add_argument("--start-year", type=int)
    ap.add_argument("--start-month", type=int)
    ap.add_argument("--start-half", type=int, choices=[1, 2])
    ap.add_argument("--end-year", type=int)
    ap.add_argument("--end-half", type=int, choices=[1, 2])
    args = ap.parse_args()

    csv_path = Path(args.input_csv)
    rows = list(csv.DictReader(csv_path.open()))
    present: Set[str] = {r.get("period", "").strip() for r in rows if r.get("period", "").strip()}

    if args.start_half is not None:
        start_half = args.start_half
    else:
        start_month = args.start_month if args.start_month is not None else ask_int("Start month at company", 1)
        start_half = 1 if start_month <= 6 else 2

    start_year = args.start_year if args.start_year is not None else ask_int("Start year at company")

    parsed = [parse_period(p) for p in present]
    parsed = [p for p in parsed if p is not None]
    if not parsed:
        raise SystemExit("No valid periods found in CSV")

    max_year, max_half = max(parsed)
    end_year = args.end_year if args.end_year is not None else max_year
    end_half = args.end_half if args.end_half is not None else max_half

    expected = expected_periods(start_year, start_half, end_year, end_half)
    missing = [p for p in expected if p not in present]

    print(f"Coverage window: {expected[0]} -> {expected[-1]}")
    print(f"Present periods: {len([p for p in expected if p in present])}")
    print(f"Missing periods: {len(missing)}")
    for p in missing:
        print(f"- {p}")


if __name__ == "__main__":
    main()
