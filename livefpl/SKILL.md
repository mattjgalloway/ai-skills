---
name: LiveFPL Price Forecast
description: Fetches LiveFPL price-change forecasts (progress now and predicted tonight) for Fantasy Premier League players. Useful for identifying players likely to rise or fall in value.
tags:
    - FPL
    - LiveFPL
    - prices
    - transfers
usage: |
    This skill exposes a single Python script that fetches the LiveFPL prices page, caches the raw HTML, and provides JSON-formatted price-change progress per player. An AI agent should call the script with the appropriate flags to select players or ranges of interest. Outputs are JSON and designed for programmatic consumption.
examples:
    - "Which players are predicted to rise now by at least 0.9?"
    - "Show me players predicted to fall tonight by at most -1.0"
    - "Does player id 666 have a predicted rise tonight?"
    - "Get pct_now and pct_tonight for players 123, 456, and 666"
---

# LiveFPL Price Forecast Skill

This skill provides a lightweight interface to the LiveFPL price predictor page (`https://www.livefpl.net/prices`). It does not rely on an API — instead it downloads and caches the page HTML, parses the embedded `data-id`, `data-now` and `data-tonight` attributes for each player, and returns a compact JSON payload.

All outputs follow a common JSON wrapper:

{
  "status": "success|info|error",
  "data": { ... },
  "message": "optional message"
}

## Script

Path: [livefpl/scripts/livefpl_prices.py](livefpl/scripts/livefpl_prices.py#L1)

## Common behavior

- Caching: The raw HTML page is cached under `livefpl/scripts/cache/fpl_cache_prices.html`. The default expiry is 12 hours.
- Force refresh: Use `--force-refresh` to bypass the cache and fetch fresh HTML. ONLY USE THIS IF YOU ABSOLUTELY NEED LIVE INFORMATION SUCH AS REQUESTED BY HUMAN.
- Output: JSON with `players` array, `fetched_at` timestamp, and `player_count`.

## Player fields

- `id`: FPL player ID (same IDs used by the FPL API)
- `pct_now`: numeric progress value representing near-term (immediate) rise/fall progress
- `pct_tonight`: numeric progress value representing predicted progress by tonight

Interpretation:
- A rise is typically when the metric >= 1.0, a fall when <= -1.0. Use numeric thresholds for fine control.

## Arguments (CLI)

- `--force-refresh` : Force fetching fresh HTML instead of using cache.
- `--player-ids <IDS...>` : Filter to the specified player IDs (space-separated).
- `--filter-gt <X>` : Numeric threshold — select metric >= X.
- `--filter-lt <X>` : Numeric threshold — select metric <= X.
- `--filter-now` : Apply the `--filter-gt/--filter-lt` to `pct_now`.
- `--filter-tonight` : Apply the `--filter-gt/--filter-lt` to `pct_tonight`.

Notes:
- If neither `--filter-now` nor `--filter-tonight` is provided, `--filter-gt`/`--filter-lt` are applied to both metrics (OR).
- Combine `--player-ids` with filters to narrow results to a specific set of players.

## Examples

- Fetch players with `pct_now >= 0.9`:

```bash
python3 livefpl/scripts/livefpl_prices.py --filter-now --filter-gt 0.9
```

- Fetch players with `pct_tonight <= -0.9`:

```bash
python3 livefpl/scripts/livefpl_prices.py --filter-tonight --filter-lt -0.9
```

- Fetch specific players (IDs 666 and 123):

```bash
python3 livefpl/scripts/livefpl_prices.py --player-ids 666 123
```

- Apply a global threshold to both now and tonight (OR behavior):

```bash
python3 livefpl/scripts/livefpl_prices.py --filter-gt 1.0
```
