#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import zlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

OBJ_RE = re.compile(rb"(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", re.S)


@dataclass
class ReviewRecord:
    file: str
    submitted: Optional[str]
    cycle_label: Optional[str]
    period: Optional[str]
    rating: Optional[str]
    rating_evidence: Optional[str]
    role: Optional[str]
    explicit_levels: str
    inferred_level: Optional[str]
    promos: str


CSV_FIELDS = [field.name for field in ReviewRecord.__dataclass_fields__.values()]


def get_objects(pdf_bytes: bytes) -> Dict[Tuple[int, int], bytes]:
    return {
        (int(m.group(1)), int(m.group(2))): m.group(3)
        for m in OBJ_RE.finditer(pdf_bytes)
    }


def get_stream(obj_body: bytes) -> Optional[bytes]:
    m = re.search(rb"stream\r?\n(.*?)\r?\nendstream", obj_body, re.S)
    if not m:
        return None
    raw = m.group(1)
    if b"/FlateDecode" in obj_body:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return None
    return raw


def parse_cmap(cmap_text: str) -> Dict[bytes, str]:
    cmap: Dict[bytes, str] = {}
    for block in re.findall(r"beginbfchar\s*(.*?)\s*endbfchar", cmap_text, re.S):
        for src_hex, dst_hex in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            src = bytes.fromhex(src_hex)
            dst = bytes.fromhex(dst_hex)
            try:
                decoded = dst.decode("utf-16-be")
            except UnicodeDecodeError:
                decoded = dst.decode("latin1", errors="ignore")
            cmap[src] = decoded
    return cmap


def decode_hex_text(hex_text: str, cmap: Dict[bytes, str]) -> str:
    raw = bytes.fromhex(hex_text)
    if not cmap:
        return "?" * max(1, len(raw))
    key_lengths = sorted({len(k) for k in cmap}, reverse=True)
    out: List[str] = []
    i = 0
    while i < len(raw):
        matched = False
        for n in key_lengths:
            token = raw[i : i + n]
            if len(token) == n and token in cmap:
                out.append(cmap[token])
                i += n
                matched = True
                break
        if not matched:
            out.append("?")
            i += 1
    return "".join(out)


def extract_lines(pdf_path: Path) -> List[str]:
    objects = get_objects(pdf_path.read_bytes())

    font_refs: Dict[str, Tuple[int, int]] = {}
    for body in objects.values():
        if b"/Font <<" in body:
            for m in re.finditer(rb"/(F\d+)\s+(\d+)\s+(\d+)\s+R", body):
                font_refs[m.group(1).decode()] = (int(m.group(2)), int(m.group(3)))
            if font_refs:
                break

    cmaps: Dict[str, Dict[bytes, str]] = {}
    for font_name, ref in font_refs.items():
        font_obj = objects.get(ref, b"")
        m = re.search(rb"/ToUnicode\s+(\d+)\s+(\d+)\s+R", font_obj)
        if not m:
            continue
        cmap_ref = (int(m.group(1)), int(m.group(2)))
        cmap_stream = get_stream(objects.get(cmap_ref, b""))
        if not cmap_stream:
            continue
        cmaps[font_name] = parse_cmap(cmap_stream.decode("latin1", errors="ignore"))

    page_objs = sorted(
        [k for k, v in objects.items() if b"/Type /Page" in v], key=lambda x: x[0]
    )

    lines: List[str] = []
    for page_ref in page_objs:
        body = objects[page_ref]
        m = re.search(rb"/Contents\s+(\d+)\s+(\d+)\s+R", body)
        if not m:
            continue
        content_ref = (int(m.group(1)), int(m.group(2)))
        stream = get_stream(objects.get(content_ref, b""))
        if not stream:
            continue
        content = stream.decode("latin1", errors="ignore")
        current_font = "F1"
        token_re = re.compile(
            r"/(F\d+)\s+[0-9.]+\s+Tf|<([0-9A-Fa-f]+)>\s*Tj|\((.*?)\)\s*Tj",
            re.S,
        )
        for m in token_re.finditer(content):
            if m.group(1):
                current_font = m.group(1)
                continue
            if m.group(2):
                text = decode_hex_text(m.group(2), cmaps.get(current_font, {}))
            else:
                text = m.group(3)
            text = " ".join(text.split())
            if text:
                lines.append(text)
    return lines


def parse_submitted(text: str) -> Optional[str]:
    m = re.search(r"\bSubmitted\s+(\d{4}-\d{2}-\d{2})\b", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\bSubmitted\s+(\d{1,2}/\d{1,2}/\d{4})\b", text, re.I)
    return m.group(1) if m else None


def parse_submitted_parts(submitted: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    if not submitted:
        return (None, None, None)
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", submitted)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})$", submitted)
    if m:
        return (int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return (None, None, None)


def parse_cycle_label(lines: List[str]) -> Optional[str]:
    head = "\n".join(lines[:80])
    patterns = [
        r"\b(Q[13]\s+20\d{2}\s+PSC)\b",
        r"\b(H[12]\s+20\d{2})\b",
        r"\b(20\d{2}\s+Mid-year)\b",
        r"\b(20\d{2}\s+Year-end)\b",
        r"\b(20\d{2})\b",
    ]
    for p in patterns:
        m = re.search(p, head, re.I)
        if m:
            return m.group(1)
    return None


def map_period(cycle_label: Optional[str], text: str, submitted: Optional[str]) -> Optional[str]:
    sub_year, sub_month, _ = parse_submitted_parts(submitted)

    if cycle_label:
        m = re.match(r"Q1\s+(20\d{2})\s+PSC", cycle_label, re.I)
        if m:
            return f"{int(m.group(1)) - 1} H2"
        m = re.match(r"Q3\s+(20\d{2})\s+PSC", cycle_label, re.I)
        if m:
            return f"{m.group(1)} H1"
        m = re.match(r"H([12])\s+(20\d{2})", cycle_label, re.I)
        if m:
            return f"{m.group(2)} H{m.group(1)}"
        m = re.match(r"(20\d{2})\s+Mid-year", cycle_label, re.I)
        if m:
            return f"{m.group(1)} H1"
        m = re.match(r"(20\d{2})\s+Year-end", cycle_label, re.I)
        if m:
            return f"{m.group(1)} H2"
        m = re.match(r"(20\d{2})$", cycle_label)
        if m:
            review_year = int(m.group(1))
            if sub_year == review_year and sub_month in {7, 8, 9}:
                return f"{review_year} H1"
            if sub_year == review_year + 1 and sub_month in {1, 2, 3}:
                return f"{review_year} H2"
            return f"{review_year} H2"

    m = re.search(r"\b(H[12])\s+(20\d{2})\b", text)
    if m:
        return f"{m.group(2)} {m.group(1)}"
    if sub_year and sub_month in {1, 2, 3}:
        return f"{sub_year - 1} H2"
    if sub_year and sub_month in {7, 8, 9}:
        return f"{sub_year} H1"
    return None


def parse_rating(text: str) -> Tuple[Optional[str], Optional[str]]:
    no_rating = re.search(r"no rating or calibration for this half", text, re.I)
    if no_rating:
        return ("No rating", no_rating.group(0))

    checks = [
        (r"Rating\s+for\s+.+?\s+is\s+([A-Za-z ]{3,40})", None),
        (r"earned\s+a\s+([A-Za-z ]{3,40})\s+rating", None),
        (r"earning\s+a\s+([A-Za-z ]{3,40})\s+this\s+half", None),
        (r"recogni[sz]ed\s+with\s+the\s+([A-Za-z ]{3,40})\s+performance\s+rating", None),
        (r"20\d{2} Year-end Ratings & Promos Calibration Notes[\s\S]{0,120}?Rating\s+([A-Za-z ]{3,40})", None),
        (r"20\d{2} Year-end Ratings? [\s\S]{0,120}?Rating\s+([A-Za-z ]{3,40})", None),
    ]

    for pat, fixed in checks:
        m = re.search(pat, text, re.I)
        if m:
            rating = fixed if fixed else m.group(1)
            rating = " ".join(rating.split())
            rating = re.sub(r"greatly\s+exceeded", "Greatly Exceeds", rating, flags=re.I)
            rating = re.sub(r"\bexceeded\s+expectations\b", "Exceeds Expectations", rating, flags=re.I)
            allowed = {
                "Meets Most Expectations",
                "Meets All Expectations",
                "Exceeds Expectations",
                "Greatly Exceeds Expectations",
                "Leave Of Absence",
            }
            rating = rating.title()
            if rating in allowed:
                return (rating, m.group(0))

    return (None, None)


def parse_role(lines: List[str]) -> Optional[str]:
    for line in lines[:25]:
        if "@" in line and ("Engineer" in line or "Manager" in line):
            return line.split("@", 1)[0].strip()
    return None


def parse_explicit_levels(text: str) -> List[str]:
    levels = sorted(
        set(
            x.upper()
            for x in re.findall(
                r"(?:\bfirst half as\s+|\bpromotion to\s+|\bpromoted to\s+|\bpromo to\s+|\bexpectations for a\s+|\btransitioned from\s+)\s*(IC\d+|E\d+|M\d+)",
                text,
                re.I,
            )
        )
    )
    return levels


def parse_level_token(level: str) -> Tuple[int, int]:
    u = level.upper()
    if u.startswith("IC"):
        return (3, int(re.sub(r"\D", "", u) or "0"))
    if u.startswith("M"):
        return (2, int(re.sub(r"\D", "", u) or "0"))
    if u.startswith("E"):
        return (1, int(re.sub(r"\D", "", u) or "0"))
    return (0, 0)


def parse_promos(text: str) -> List[str]:
    promos = []
    patterns = [
        r"promotion to\s+((?:IC|E)\d+)",
        r"promoted to\s+((?:IC|E)\d+)",
        r"transitioned from\s+(M\d+)\s+to\s+SWE",
        r"first half as\s+((?:IC|E)\d+)",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            promos.append(" ".join(m.group(0).split()))
    # stable order, dedupe
    uniq = []
    for p in promos:
        if p.lower() not in [x.lower() for x in uniq]:
            uniq.append(p)
    return uniq


def period_key(period: Optional[str]) -> Tuple[int, int]:
    if not period:
        return (9999, 9)
    m = re.match(r"(\d{4})\s+H([12])", period)
    if not m:
        return (9999, 9)
    return (int(m.group(1)), int(m.group(2)))


def infer_level(period: Optional[str], role: Optional[str], text: str, explicit_levels: List[str]) -> Optional[str]:
    # Prefer explicit level signals when present.
    if explicit_levels:
        return sorted(explicit_levels, key=parse_level_token)[-1]

    # Generic role-based fallback only.
    if role:
        if "Manager" in role:
            return "Manager (inferred from role)"
        if "Engineer" in role:
            return "Engineer (inferred from role)"
    return None


def analyze_pdf(pdf_path: Path) -> ReviewRecord:
    lines = extract_lines(pdf_path)
    text = "\n".join(lines)

    submitted = parse_submitted(text)
    cycle_label = parse_cycle_label(lines)
    period = map_period(cycle_label, text, submitted)
    rating, rating_evidence = parse_rating(text)
    role = parse_role(lines)
    explicit_levels = parse_explicit_levels(text)
    promos = parse_promos(text)
    inferred_level = infer_level(period, role, text, explicit_levels)

    return ReviewRecord(
        file=pdf_path.name,
        submitted=submitted,
        cycle_label=cycle_label,
        period=period,
        rating=rating,
        rating_evidence=rating_evidence,
        role=role,
        explicit_levels=", ".join(explicit_levels),
        inferred_level=inferred_level,
        promos="; ".join(promos),
    )


def period_sort_key(period: Optional[str]) -> Tuple[int, int, str]:
    if not period:
        return (9999, 9, "")
    m = re.match(r"(\d{4})\s+H([12])", period)
    if not m:
        return (9999, 9, period)
    return (int(m.group(1)), int(m.group(2)), period)


def write_csv(path: Path, records: List[ReviewRecord]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in records:
            w.writerow(asdict(r))


def write_json(path: Path, records: List[ReviewRecord]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2)


def write_markdown(path: Path, records: List[ReviewRecord]) -> None:
    headers = ["Period", "Submitted", "Rating", "Level", "Role", "Promo", "File"]
    with path.open("w", encoding="utf-8") as f:
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("|" + "|".join(["---"] * len(headers)) + "|\n")
        for r in records:
            row = [
                r.period or "",
                r.submitted or "",
                r.rating or "",
                r.inferred_level or "",
                r.role or "",
                r.promos or "",
                r.file,
            ]
            f.write("| " + " | ".join(x.replace("|", "\\|") for x in row) + " |\n")


def safe_stem(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "review"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze PSC review PDFs")
    parser.add_argument("--input-dir", default=".", help="Directory with PDF files")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument(
        "--dump-text-dir",
        default="output/review_text",
        help="Directory to write decoded review text files",
    )
    parser.add_argument(
        "--no-dump-text",
        action="store_true",
        help="Do not write decoded full-text review files",
    )
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_dir = None if args.no_dump_text else Path(args.dump_text_dir)
    if dump_dir is not None:
        dump_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(in_dir.glob("*.pdf"))
    records: List[ReviewRecord] = []
    for p in pdfs:
        lines = extract_lines(p)
        text = "\n".join(lines)
        if dump_dir is not None:
            (dump_dir / f"{safe_stem(p.stem)}.txt").write_text(text, encoding="utf-8")

        submitted = parse_submitted(text)
        cycle_label = parse_cycle_label(lines)
        period = map_period(cycle_label, text, submitted)
        rating, rating_evidence = parse_rating(text)
        role = parse_role(lines)
        explicit_levels = parse_explicit_levels(text)
        promos = parse_promos(text)
        inferred_level = infer_level(period, role, text, explicit_levels)

        records.append(
            ReviewRecord(
                file=p.name,
                submitted=submitted,
                cycle_label=cycle_label,
                period=period,
                rating=rating,
                rating_evidence=rating_evidence,
                role=role,
                explicit_levels=", ".join(explicit_levels),
                inferred_level=inferred_level,
                promos="; ".join(promos),
            )
        )
    records.sort(key=lambda r: (period_sort_key(r.period), r.file))

    write_csv(out_dir / "reviews_analysis.csv", records)
    write_json(out_dir / "reviews_analysis.json", records)
    write_markdown(out_dir / "reviews_analysis.md", records)

    print(f"Analyzed {len(records)} PDFs")
    print(f"Wrote: {out_dir / 'reviews_analysis.csv'}")
    print(f"Wrote: {out_dir / 'reviews_analysis.json'}")
    print(f"Wrote: {out_dir / 'reviews_analysis.md'}")
    if dump_dir is not None:
        print(f"Wrote text files to: {dump_dir}")
    else:
        print("Skipped decoded text files")


if __name__ == "__main__":
    main()
