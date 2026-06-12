#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple


@dataclass
class Row:
    period: str
    submitted: str
    rating: str
    level: str
    promo: str
    file: str


def parse_period(period: str) -> Tuple[int, int]:
    m = re.match(r"(\d{4})\s+H([12])", period or "")
    if not m:
        return (9999, 9)
    return (int(m.group(1)), int(m.group(2)))


def level_bucket(level: str) -> str:
    if not level:
        return "Unknown"
    u = level.upper()
    if re.match(r"^(IC|E)\d+\b", u):
        return "IC"
    if re.match(r"^M\d+\b", u):
        return "Manager"
    return "Unknown"


def read_rows(csv_path: Path) -> List[Row]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        raw = list(csv.DictReader(f))
    best: Dict[str, dict] = {}
    for r in raw:
        p = r.get("period", "").strip()
        if not p:
            continue
        cur = best.get(p)
        score = (
            1 if (r.get("rating") or "").strip() else 0,
            1 if (r.get("submitted") or "").strip() else 0,
            -len(r.get("file") or ""),
        )
        if cur is None:
            best[p] = r
            continue
        cur_score = (
            1 if (cur.get("rating") or "").strip() else 0,
            1 if (cur.get("submitted") or "").strip() else 0,
            -len(cur.get("file") or ""),
        )
        if score > cur_score:
            best[p] = r

    rows = [
        Row(
            period=p,
            submitted=(r.get("submitted") or "-").strip() or "-",
            rating=(r.get("rating") or "-").strip() or "-",
            level=(r.get("inferred_level") or "-").strip() or "-",
            promo=(r.get("promos") or "-").strip() or "-",
            file=(r.get("file") or "-").strip() or "-",
        )
        for p, r in best.items()
    ]
    rows.sort(key=lambda x: parse_period(x.period))
    return rows


def contiguous_phase_summary(rows: List[Row]) -> List[Tuple[str, str, str, str]]:
    if not rows:
        return []
    phases: List[Tuple[str, str, str, str]] = []
    s = rows[0]
    current_bucket = level_bucket(s.level)
    start_period = s.period
    last_period = s.period
    last_level = s.level
    for r in rows[1:]:
        b = level_bucket(r.level)
        if b != current_bucket:
            phases.append((start_period, last_period, current_bucket, last_level))
            current_bucket = b
            start_period = r.period
        last_period = r.period
        last_level = r.level
    phases.append((start_period, last_period, current_bucket, last_level))
    return phases


def write_markdown(out_path: Path, rows: List[Row]) -> None:
    ratings = Counter(r.rating for r in rows if r.rating != "-")
    phases = contiguous_phase_summary(rows)

    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Career Trajectory Summary\n\n")
        if rows:
            f.write(f"Coverage: **{rows[0].period} -> {rows[-1].period}** ({len(rows)} periods with reviews)\n\n")

        f.write("## Rating Distribution\n\n")
        if ratings:
            for k, v in ratings.most_common():
                f.write(f"- {k}: {v}\n")
        else:
            f.write("- No explicit ratings found.\n")

        f.write("\n## Level Phases\n\n")
        if phases:
            for a, b, bucket, lvl in phases:
                f.write(f"- {a} -> {b}: {bucket} track (latest level signal: {lvl})\n")
        else:
            f.write("- No level phases inferred.\n")

        f.write("\n## Key Inflection Points\n\n")
        for r in rows:
            flags = []
            if r.promo != "-":
                flags.append(f"promo/milestone: {r.promo}")
            if r.rating in {"Greatly Exceeds Expectations", "Meets Most Expectations", "Leave Of Absence", "No rating"}:
                flags.append(f"rating: {r.rating}")
            if flags:
                f.write(f"- {r.period}: " + "; ".join(flags) + "\n")

        f.write("\n## Period Table\n\n")
        f.write("| Period | Submitted | Rating | Level | Promo | File |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in rows:
            vals = [r.period, r.submitted, r.rating, r.level, r.promo, r.file]
            vals = [v.replace("|", "\\|") for v in vals]
            f.write("| " + " | ".join(vals) + " |\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a career trajectory summary from reviews_analysis.csv")
    ap.add_argument("--input-csv", default="output/reviews_analysis.csv")
    ap.add_argument("--output-md", default="output/trajectory_summary.md")
    args = ap.parse_args()

    rows = read_rows(Path(args.input_csv))
    out = Path(args.output_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(out, rows)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
