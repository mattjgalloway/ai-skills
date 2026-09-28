---
name: "FPL Data Access"
description: "Access FPL API data including price changes"
tags:
    - FPL
    - Fantasy Premier League
    - Football
usage: |
    This skill provides access to multiple Python scripts for retrieving Fantasy Premier League (FPL) data. The AI agent should select the appropriate script based on the user's request. All outputs are in JSON format.
examples:
    - "Get all FPL teams"
    - "Show me all players with a price between 7.0m and 9.0m"
    - "Find midfielders from Liverpool"
    - "Show all currently flagged Arsenal players"
    - "Check the availability of my Gameweek 6 squad"
    - "Show players likely to rise in price tonight"
    - "Find Arsenal players falling by at least 80 percent on the projected price-change metric"
    - "What are the details for Gameweek 18?"
    - "What's the overall rank for FPL team ID 12345?"
    - "Show me the transfer history for my FPL team (ID 12345)"
    - "What players did FPL team 12345 pick in Gameweek 24?"
    - "Force a refresh of all general FPL data and show me all forwards."
    - "Get my FPL team's details and history (team ID 12345), forcing a refresh."
---

# FPL Data Access Skill

This skill allows an AI agent to fetch comprehensive data from the Fantasy Premier League (FPL) API. It includes scripts for general game-wide data, official price-change prediction data, manager-specific entry data, fixtures, live gameweek data, and league standings. Outputs are JSON-formatted for programmatic consumption.

## Common Functionality

Shared behavior across scripts:

- Caching: API responses are cached under a `cache` directory located relative to the `fpl/scripts` directory by default. Cache files are named using a `fpl_cache_<key>.json` pattern.
- Force refresh: All scripts accept a `--force-refresh` flag which, when provided, forces a fresh fetch from the API and bypasses cache. ONLY USE FORCE REFRESH IF YOU REALLY NEED FRESH DATA LIKE YOU'RE GETTING LIVE GAMEWEEK DATA AND ONLY ON API CALLS THAT MIGHT HAVE SOME CHANGED DATA.
- Output format: All scripts produce JSON with the structure `{ "status": "success|info|error", "data": <payload>, "message": <optional> }`.

When reading per-script documentation below, assume `--force-refresh` and the JSON output format behave as described here.

## 1. General FPL Data (`fpl_data.py`)

Retrieve broad FPL data such as lists of all teams, players, or gameweeks, with various player filtering options.

### Arguments for `fpl_data.py`

* `--gameweeks`: Retrieves a list of all gameweeks (events) with details like ID, name, deadline, average score, and top-scoring player info. Example: `python fpl_data.py --gameweeks`

* `--teams`: Retrieves a list of all Premier League teams with their ID, name, short name, and strength rating. Example: `python fpl_data.py --teams`

* Player filtering: Use the following flags to query players and return matching results: `--player`, `--player-ids`, `--team`, `--team-id`, `--position`, `--min-price`, `--max-price`, `--availability`. Example: `python fpl_data.py --position MID --min-price 6.0`

* `--player <PLAYER_NAME_PARTIAL>`: Filter players by partial/full name (case-insensitive). Example: `python fpl_data.py --player "Salah"`

* `--player-ids <PLAYER_IDS...>`: Filter by multiple player IDs (space-separated). Example: `python fpl_data.py --player-ids 123 456 789`

* `--team <TEAM_NAME_PARTIAL>`: Filter players by team name (resolves to team ID). Example: `python fpl_data.py --team "Arsenal"`

* `--team-id <TEAM_ID>`: Filter players by team ID. Example: `python fpl_data.py --team-id 1`

* `--position <POSITION_ABBREVIATION>`: Filter by position (`GKP`, `DEF`, `MID`, `FWD`). Example: `python fpl_data.py --position DEF`

* `--min-price <PRICE_FLOAT>` / `--max-price <PRICE_FLOAT>`: Price filters (in millions). Example: `python fpl_data.py --min-price 6.0 --max-price 8.5`

* `--availability all|flagged|available|doubtful|injured|suspended|unavailable`: Return official player availability fields, optionally filtered to a status group. `flagged` means any status other than available. Example: `python fpl_data.py --team Arsenal --availability flagged`

* `--limit <1-50>` / `--offset <N>`: Read a bounded page of player results. The default and maximum page size is 50. Example: `python fpl_data.py --position MID --limit 50 --offset 50`

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

### Results limit

- **Limit:** Player-list responses are always bounded to at most 50 players per page. There is no unlimited-output option.
- **Pagination:** Responses include `player_count`, `returned_count`, `offset`, `limit`, `has_more`, and `next_offset`. When `has_more` is true, request the next bounded page using `--offset <next_offset>`.
- **How to avoid pagination:** Narrow results using filters such as `--player`, `--player-ids`, `--team`, `--team-id`, `--position`, `--availability`, `--min-price`, or `--max-price`.

### Availability output fields

Player records include `status`, the normalized `availability` label, `chance_of_playing_this_round`, `chance_of_playing_next_round`, `news`, `news_added`, `can_select`, `can_transact`, and `removed`.

---

## 2. Price-Change Data (`fpl_price_changes.py`)

Search official FPL price predictor fields for players likely to rise or fall. Uses `bootstrap-static`, shares the same cache as `fpl_data.py`, and returns capped JSON player lists.

### Arguments for `fpl_price_changes.py`

* Player filtering: Use `--player`, `--player-ids`, `--team`, `--team-id`, `--position`, `--min-price`, or `--max-price` to narrow the player pool before applying price-change filters.

* `--rising`: Return players whose selected price-change metric is at or above `--threshold`. Example: `python fpl_price_changes.py --rising --threshold 80 --metric projected`

* `--falling`: Return players whose selected price-change metric is at or below negative `--threshold`. Example: `python fpl_price_changes.py --falling --threshold 90 --position MID`

* `--threshold <PERCENT>`: Threshold used by `--rising` and `--falling`; default is `100.0`.

* `--metric current|projected|both`: Select `price_change_percent`, the requested projection from `price_change_projections`, or either metric. Default is `projected`.

* `--projection-offset <N>`: Projection offset to read from `price_change_projections`; default is `0`, the nearest official projection.

* `--min-percent <PERCENT>` / `--max-percent <PERCENT>`: Explicit percentage range filters for the selected metric. Example: `python fpl_price_changes.py --team Arsenal --metric both --min-percent 50`

* `--limit <1-50>` / `--offset <N>`: Read a bounded page of price-change results. The default and maximum page size is 50.

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

### Price-change output fields

Each returned player includes common player identity fields plus:

- `price_change_percent`: official current progress percentage
- `price_change_hourly_rate`: official hourly trend
- `projected_percent`: projected percentage for the requested offset
- `projection_likelihood`: official likelihood value for the requested projection
- `projection_offset`: projection offset used
- `price_change_locked_until`: lock status when present
- `price_change_calibrating`: calibration status

### Results limit

- **Limit:** The script always returns at most 50 players per page. There is no unlimited-output option.
- **Pagination:** Use the response's `has_more` and `next_offset` fields with `--offset` to fetch the next bounded page.
- **How to avoid pagination:** Narrow results using player, team, position, price, metric, threshold, `--min-percent`, or `--max-percent` filters.

---

## 3. FPL Manager Entry Data (`fpl_entry_data.py`)

Retrieve data for a specific FPL entry (manager/team). `entry_id` is required for relevant operations.

### Arguments for `fpl_entry_data.py`

* `entry_id <ENTRY_ID>` (required positional): The unique FPL team ID. Example: `python fpl_entry_data.py 12345 --details`

* `--details`: Fetch general entry details (team name, manager, overall points and rank). Example: `python fpl_entry_data.py 12345 --details`

* `--history`: Retrieve historical performance per gameweek. Example: `python fpl_entry_data.py 12345 --history`

* `--transfers`: Retrieve the entry's transfer history. Example: `python fpl_entry_data.py 12345 --transfers`

* `--picks <GAMEWEEK_NUMBER>`: Retrieve the picks for a specific gameweek. Example: `python fpl_entry_data.py 12345 --picks 24`

* `--availability <GAMEWEEK_NUMBER>`: Join that gameweek's 15 entry picks to current official player availability, including status, chance-of-playing, news, selection and transaction fields. Example: `python fpl_entry_data.py 12345 --availability 24`

* `--flagged-only`: With `--availability`, return only players whose official status is not available. Example: `python fpl_entry_data.py 12345 --availability 24 --flagged-only`

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

---

## 4. Fixtures Data (`fpl_fixture_data.py`)

Fetch fixtures for the season or a specific gameweek.

### Arguments for `fpl_fixture_data.py`

* `--fixtures`: Return the list of fixtures for the season. Example: `python fpl_fixture_data.py --fixtures`

* `--gameweek <N>`: Return fixtures for gameweek `N`. Example: `python fpl_fixture_data.py --gameweek 24`

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

### Fixture output fields

Each fixture object returned by the script includes common fields from the API plus score information when available:

- `id`: Fixture ID
- `event`: Gameweek/event number
- `team_h`: Home team ID
- `team_a`: Away team ID
- `team_h_difficulty`, `team_a_difficulty`: Difficulty ratings
- `minutes`, `started`, `finished`: status flags
- `kickoff_time`: kickoff timestamp
- `team_h_score`, `team_a_score`: scores for each side (present when the match has finished or the API provides them)
- `score`: formatted string like `2-1` when both scores are available, otherwise `null`

---

## 5. Live Gameweek Data (`fpl_live_gameweek.py`)

Fetch live per-player and event statistics for a specific gameweek. The `--gameweek` argument is required.

### Arguments for `fpl_live_gameweek.py`

* `--gameweek <N>` (required): Fetch live data for the specified gameweek number `N`. Example: `python fpl_live_gameweek.py --gameweek 24`

* `--player-ids <PLAYER_IDS...>` (required): Filter by multiple player IDs (space-separated). Example: `python fpl_live_gameweek.py --player-ids 123 456 789`

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

### Live output fields

The script returns an object containing:

- `gameweek`: Provided gameweek number
- `elements`: Array of player live objects (`id`, `stats`, `explain`)
- `events`: Array of event-level summaries (`id`, `stats`)

---

## 6. League Standings (`fpl_league_standings.py`)

Fetch classic league details and standings for a given league.

API endpoint:

- League standings: `https://fantasy.premierleague.com/api/leagues-classic/LID/standings/?page_standings=P` (replace `LID` with league id and `P` with page number)

### Arguments for `fpl_league_standings.py`

* `league_id` (required positional): The classic league ID to query. Example: `python fpl_league_standings.py 12345`

* `--page <N>`: The page of standings to fetch (default `1`). Example: `python fpl_league_standings.py 12345 --page 1`

* `--force-refresh`: See Common Functionality for caching and refresh behavior.

### Output fields

The script returns a JSON object containing:

- `league`: The league metadata returned by the API (name, id, etc.)
- `standings`: Array of simplified standing entries (rank, entry id, player_name, entry_name, total, event_total, last_rank, movement)
- `page`: Pagination information (`page`, `results`, `has_next`, `has_previous`)
