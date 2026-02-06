---
name: FPL Data Access
description: Accesses comprehensive data from the Fantasy Premier League API, covering general game statistics (teams, players, gameweeks) and specific FPL manager entry details (history, transfers, picks).
tags:
    - FPL
    - Fantasy Premier League
    - Football
usage: |
  This skill provides access to two Python scripts for retrieving Fantasy Premier League (FPL) data.

  The AI agent should select the appropriate script based on the user's request. All outputs are in JSON format.
examples:
    - "Get all FPL teams"
    - "Show me all players with a price between 7.0m and 9.0m"
    - "Find midfielders from Liverpool"
    - "What are the details for Gameweek 18?"
    - "What's the overall rank for FPL team ID 2359318?"
    - "Show me the transfer history for my FPL team (ID 12345)"
    - "What players did FPL team 2359318 pick in Gameweek 24?"
    - "Force a refresh of all general FPL data and show me all forwards."
    - "Get my FPL team's details and history (team ID 2359318), forcing a refresh."
---

# FPL Data Access Skill

This skill allows an AI agent to fetch comprehensive data from the Fantasy Premier League (FPL) API. It encompasses two distinct scripts: one for general game-wide data (`fpl_data.py`) and another for manager-specific entry data (`fpl_entry_data.py`). The output from both scripts is consistently in JSON format for easy programmatic consumption by the AI.

## Common Functionality

The scripts in this repository share common behavior and conventions. Refer to this section for shared features instead of repeating them per-script.

- Caching: API responses are cached under a `cache` directory located relative to the `fpl/scripts` directory by default. Cache files are named using a `fpl_cache_<key>.json` pattern.
- Force refresh: All scripts accept a `--force-refresh` flag which, when provided, forces a fresh fetch from the API and bypasses cache.
- Output format: All scripts produce JSON with the structure `{ "status": "success|info|error", "data": <payload>, "message": <optional> }` for programmatic consumption.

When reading per-script documentation below, assume `--force-refresh` and the JSON output format behave as described here.

# FPL Data Access Skill

This skill allows an AI agent to fetch comprehensive data from the Fantasy Premier League (FPL) API. It encompasses two distinct scripts: one for general game-wide data (`fpl_data.py`) and another for manager-specific entry data (`fpl_entry_data.py`). The output from both scripts is consistently in JSON format for easy programmatic consumption by the AI.

## 1. General FPL Data (`fpl_data.py`)

This script is used to retrieve broad FPL data such as lists of all teams, players, or gameweeks, with various filtering options for players.

### Arguments for `fpl_data.py`

All arguments can be combined to refine queries.

*   `--gameweeks`:
        *   **Description**: Retrieves a list of all gameweeks (events) with pertinent details like ID, name, deadline, average score, and top-scoring player info.
        *   **Example**: `python fpl_data.py --gameweeks`

*   `--teams`:
        *   **Description**: Retrieves a list of all Premier League teams with their ID, name, short name, and strength rating.
        *   **Example**: `python fpl_data.py --teams`

*   `--players`:
        *   **Description**: Retrieves a list of players. If no other filtering arguments are provided, it returns a limited list (e.g., first 10 for brevity) of all players. When combined with other player-filtering arguments, it returns the full list of players matching those criteria.
        *   **Example**: `python fpl_data.py --players`
        *   **Example (with filter)**: `python fpl_data.py --players --position MID`

*   `--player <PLAYER_NAME_PARTIAL>`:
        *   **Description**: Filters players by a partial or full player name (case-insensitive).
        *   **Type**: String
        *   **Example**: `python fpl_data.py --player "Salah"`

*   `--player-id <PLAYER_ID>`:
        *   **Description**: Filters players by their unique player ID.
        *   **Type**: Integer
        *   **Example**: `python fpl_data.py --player-id 123`

*   `--team <TEAM_NAME_PARTIAL>`:
        *   **Description**: Filters players by a partial or full team name (case-insensitive). The script will attempt to resolve the team name to an ID. If multiple teams match, an error will be returned.
        *   **Type**: String
        *   **Example**: `python fpl_data.py --team "Arsenal"`

*   `--team-id <TEAM_ID>`:
        *   **Description**: Filters players by their unique team ID.
        *   **Type**: Integer
        *   **Example**: `python fpl_data.py --team-id 1`

*   `--position <POSITION_ABBREVIATION>`:
        *   **Description**: Filters players by their position. Valid values include `GKP` (Goalkeeper), `DEF` (Defender), `MID` (Midfielder), `FWD` (Forward). Case-insensitive.
        *   **Type**: String
        *   **Example**: `python fpl_data.py --position DEF`

*   `--min-price <PRICE_FLOAT>`:
        *   **Description**: Filters players by a minimum price (in millions, e.g., 4.5 for £4.5M).
        *   **Type**: Float
        *   **Example**: `python fpl_data.py --min-price 6.0`

*   `--max-price <PRICE_FLOAT>`:
        *   **Description**: Filters players by a maximum price (in millions, e.g., 10.0 for £10.0M).
        *   **Type**: Float
        *   **Example**: `python fpl_data.py --max-price 8.5`

*   `--force-refresh`:
        *   **See**: Common Functionality section for caching and `--force-refresh` behavior.

---

## 2. FPL Manager Entry Data (`fpl_entry_data.py`)

This script retrieves specific data related to a particular FPL manager's entry (team). An `entry_id` is required for all operations.

### Arguments for `fpl_entry_data.py`

*   `entry_id <ENTRY_ID>` (Required, first argument):
        *   **Description**: The unique FPL team ID for which to fetch data.
        *   **Type**: Integer
        *   **Example**: `python fpl_entry_data.py 2359318 --details`

*   `--details`:
        *   **Description**: Retrieves general details about the FPL entry, such as the team name, manager's name, overall points and rank, current gameweek, and a summary of leagues.
        *   **Example**: `python fpl_entry_data.py 2359318 --details`

*   `--history`:
        *   **Description**: Retrieves historical performance data for the FPL entry, including points, ranks, value, and bank per gameweek for the current season, past season summaries, and chips played.
        *   **Example**: `python fpl_entry_data.py 2359318 --history`

*   `--transfers`:
        *   **Description**: Retrieves a list of all player transfers made by the FPL entry, including the gameweek, timestamp, and the IDs and costs of players transferred in and out.
        *   **Example**: `python fpl_entry_data.py 2359318 --transfers`

*   `--picks <GAMEWEEK_NUMBER>`:
        *   **Description**: Retrieves details about the players selected by the FPL entry for a specific gameweek, including captain/vice-captain choices and automatic substitutions.
        *   **Type**: Integer
        *   **Example**: `python fpl_entry_data.py 2359318 --picks 24`

*   `--force-refresh`:
        *   **See**: Common Functionality section for caching and `--force-refresh` behavior.

---


## 3. Fixtures Data (`fpl_fixture_data.py`)

This script fetches fixture information from the FPL API. It can return all fixtures or the fixtures for a specific gameweek (event). The API endpoints used are:

- All fixtures: `https://fantasy.premierleague.com/api/fixtures/`
- Fixtures for a gameweek: `https://fantasy.premierleague.com/api/fixtures/?event=GW` (replace `GW` with the gameweek number)

### Arguments for `fpl_fixture_data.py`

* `--fixtures`:
    * **Description**: Returns a list of fixtures for the season (or from cache).
    * **Example**: `python fpl_fixture_data.py --fixtures`

* `--gameweek <N>`:
    * **Description**: Returns fixtures for the specific gameweek number `N`.
    * **Type**: Integer
    * **Example**: `python fpl_fixture_data.py --gameweek 24`

* `--force-refresh`:
        * **See**: Common Functionality section for caching and `--force-refresh` behavior.

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
