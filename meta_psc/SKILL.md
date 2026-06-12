# Performance Review PDF Analysis Skill

## Purpose
Analyze a folder of performance-review PDFs and produce:
- structured per-review metadata (`period`, `submitted`, `rating`, `level signals`, `promo milestones`)
- decoded full text for each review (for deep qualitative analysis)
- a trajectory summary report
- a missing-period coverage check using user-provided start date

This skill is rerunnable as new reviews are added.

## Privacy
Performance review PDFs and generated outputs can contain sensitive personal and
employment information. Keep input PDFs, decoded text, and generated output files
out of git unless they have been intentionally anonymized.

## Scripts
- `scripts/review_analyzer.py`
- `scripts/trajectory_summary.py`
- `scripts/review_coverage_check.py`

## Input Assumptions
- Review PDFs are in the working folder.
- Filenames can vary; parsing is based on PDF contents.

## Runbook

### 1) Extract structured data + decoded text
```bash
./scripts/review_analyzer.py --input-dir . --output-dir output --dump-text-dir output/review_text
```

Outputs:
- `output/reviews_analysis.csv`
- `output/reviews_analysis.json`
- `output/reviews_analysis.md`
- decoded text files in `output/review_text/*.txt`

Use `--no-dump-text` if you only want structured outputs and do not want decoded
full-text review files written to disk.

### 2) Generate trajectory summary
```bash
./scripts/trajectory_summary.py --input-csv output/reviews_analysis.csv --output-md output/trajectory_summary.md
```

Output:
- `output/trajectory_summary.md`

### 3) Check missing periods (interactive)
If start date/cadence context is not known, this script asks for it.

```bash
./scripts/review_coverage_check.py --input-csv output/reviews_analysis.csv
```

Optional non-interactive mode:
```bash
./scripts/review_coverage_check.py \
  --input-csv output/reviews_analysis.csv \
  --start-year 2020 --start-month 1 --end-year 2024 --end-half 2
```

## Questions To Ask (when context missing)
1. What year and month did you join?
2. Is review cadence semi-annual (H1/H2)?
3. Up to which cycle should coverage be evaluated?

## Quick Validation Commands

### Dedupe table by period (prefer rows with explicit rating)
```bash
python3 - <<'PY'
import csv
rows=list(csv.DictReader(open('output/reviews_analysis.csv')))
best={}
for r in rows:
    p=r.get('period','').strip()
    if not p: continue
    s=(1 if r.get('rating') else 0, 1 if r.get('submitted') else 0)
    if p not in best or s>(1 if best[p].get('rating') else 0, 1 if best[p].get('submitted') else 0):
        best[p]=r
for p in sorted(best):
    r=best[p]
    print(p, '|', r.get('rating') or '-', '|', r.get('inferred_level') or '-', '|', r.get('promos') or '-')
PY
```

### Pull key snippets from decoded text
```bash
rg -n "Submitted|Rating|promotion|promoted|transitioned|first half as|Role:|Rationale" output/review_text/*.txt
```

## Narrative Output Pattern
Use `output/trajectory_summary.md` + specific citations from `output/review_text/*.txt`.

Deliverables to produce:
1. Short narrative (8-12 lines): role phases, inflection points, trend.
2. Strengths/growth timeline by era.
3. Optional promo storyline framing.

## Caveats
- Some templates (often mid-year) omit explicit ratings.
- Duplicate exports may exist for one period (draft/final).
- Level inference is conservative: explicit signals first, role-based fallback second.
- PDF text extraction is intentionally lightweight. It handles common Meta PSC
  exports, but it is not a complete PDF text engine.

## Re-run Procedure
1. Add new PDFs to folder.
2. Run analyzer.
3. Run trajectory summary.
4. Run coverage checker (interactive or with explicit args).
5. Refresh narrative outputs from regenerated artifacts.

## Tests
```bash
python3 -m unittest discover -s tests
```
