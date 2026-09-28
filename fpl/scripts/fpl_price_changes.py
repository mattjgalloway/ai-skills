import argparse
import unicodedata
from typing import Any, Dict, List, Optional

from fpl_utils import FPLUtils, MAX_PLAYERS, format_json_output


BASE_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


def normalize_str(s: Optional[str]) -> str:
    if s is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def parse_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_maps(data: Dict[str, Any]) -> tuple[Dict[int, str], Dict[Any, Any]]:
    team_name_map = {team.get("id"): team.get("name") for team in data.get("teams", [])}
    position_map: Dict[Any, Any] = {}
    for element_type in data.get("element_types", []):
        position_map[element_type.get("id")] = element_type.get("singular_name_short")
        if element_type.get("singular_name"):
            position_map[element_type["singular_name"].lower()] = element_type.get("id")
        if element_type.get("plural_name_short"):
            position_map[element_type["plural_name_short"].lower()] = element_type.get("id")
    return team_name_map, position_map


def resolve_team_id(data: Dict[str, Any], team_name: Optional[str], team_id: Optional[int]) -> tuple[Optional[int], Optional[str], Optional[str]]:
    if not team_name:
        if team_id is not None:
            return team_id, f"Filtering by team ID: {team_id}", None
        return team_id, None, None

    search_team = normalize_str(team_name)
    matches = [
        team.get("id")
        for team in data.get("teams", [])
        if search_team in normalize_str(team.get("name")) or search_team in normalize_str(team.get("short_name"))
    ]

    if len(matches) == 1:
        if team_id is not None and team_id != matches[0]:
            return team_id, f"Warning: Both --team '{team_name}' (ID {matches[0]}) and --team-id '{team_id}' were provided and conflict. Using --team-id: {team_id}.", None
        return matches[0], f"Filtering by team name: '{team_name}' (Resolved to ID: {matches[0]})", None
    if len(matches) > 1:
        names = [team.get("name") for team in data.get("teams", []) if team.get("id") in matches]
        return team_id, None, f"Multiple teams found for '{team_name}': {names}. Please be more specific or use --team-id."
    if team_id is None:
        return team_id, None, f"No team found matching '{team_name}'. Please check the name."
    return team_id, f"Filtering by team ID: {team_id}", None


def projection_for_offset(player: Dict[str, Any], offset: int) -> Dict[str, Any]:
    projections = player.get("price_change_projections") or []
    for projection in projections:
        if projection.get("offset") == offset:
            return projection
    return {}


def metric_values(player: Dict[str, Any], metric: str) -> List[float]:
    values: List[float] = []
    current = player.get("price_change_percent")
    projected = player.get("projected_percent")
    if metric in ("current", "both") and current is not None:
        values.append(current)
    if metric in ("projected", "both") and projected is not None:
        values.append(projected)
    return values


def selected_sort_value(player: Dict[str, Any], metric: str) -> float:
    values = metric_values(player, metric)
    if not values:
        return 0.0
    return max(values, key=lambda value: abs(value))


def filter_players(
    data: Dict[str, Any],
    name: Optional[str],
    player_ids: Optional[List[int]],
    team_id: Optional[int],
    position: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    projection_offset: int,
) -> List[Dict[str, Any]]:
    team_name_map, position_map = build_maps(data)
    ids = set(player_ids) if player_ids else None
    target_position_id = position_map.get(position.lower()) if position else None
    players: List[Dict[str, Any]] = []

    for player in data.get("elements", []):
        now_cost = player.get("now_cost")
        price = now_cost / 10.0 if now_cost is not None else None
        first_name = player.get("first_name", "")
        second_name = player.get("second_name", "")
        full_name = f"{first_name} {second_name}".strip()
        player_team_id = player.get("team")
        element_type = player.get("element_type")

        if name and normalize_str(name) not in normalize_str(full_name) and normalize_str(name) not in normalize_str(player.get("web_name")):
            continue
        if ids is not None and player.get("id") not in ids:
            continue
        if team_id is not None and team_id != player_team_id:
            continue
        if position and target_position_id != element_type:
            continue
        if min_price is not None and (price is None or price < min_price):
            continue
        if max_price is not None and (price is None or price > max_price):
            continue

        projection = projection_for_offset(player, projection_offset)
        players.append({
            "id": player.get("id"),
            "first_name": first_name,
            "second_name": second_name,
            "web_name": player.get("web_name"),
            "full_name": full_name,
            "team_id": player_team_id,
            "team_name": team_name_map.get(player_team_id, "Unknown Team"),
            "element_type": element_type,
            "position": position_map.get(element_type, "Unknown"),
            "now_cost": price,
            "status": player.get("status"),
            "selected_by_percent": player.get("selected_by_percent"),
            "price_change_percent": parse_float(player.get("price_change_percent")),
            "price_change_hourly_rate": parse_float(player.get("price_change_hourly_rate")),
            "projected_percent": parse_float(projection.get("projected_percent")),
            "projection_likelihood": projection.get("likelihood"),
            "projection_offset": projection.get("offset", projection_offset),
            "price_change_locked_until": player.get("price_change_locked_until"),
            "price_change_calibrating": player.get("price_change_calibrating"),
        })
    return players


def apply_price_filters(players: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    filtered = []
    for player in players:
        values = metric_values(player, args.metric)
        if not values:
            continue

        keep = True
        if args.rising:
            keep = keep and any(value >= args.threshold for value in values)
        if args.falling:
            keep = keep and any(value <= -args.threshold for value in values)
        if args.min_percent is not None:
            keep = keep and any(value >= args.min_percent for value in values)
        if args.max_percent is not None:
            keep = keep and any(value <= args.max_percent for value in values)
        if keep:
            filtered.append(player)
    return filtered


def main() -> None:
    parser = argparse.ArgumentParser(description="Search official FPL price-change predictor data.")
    parser.add_argument("--player", type=str, help="Filter players by player name or web name (case-insensitive, partial match).")
    parser.add_argument("--player-ids", type=int, nargs="+", help="Filter players by multiple player IDs (space-separated).")
    parser.add_argument("--team", type=str, help="Filter players by team name (case-insensitive, partial match).")
    parser.add_argument("--team-id", type=int, help="Filter players by team ID.")
    parser.add_argument("--position", type=str, help="Filter players by position (GKP, DEF, MID, FWD).")
    parser.add_argument("--min-price", type=float, help="Minimum player cost (e.g., 4.5).")
    parser.add_argument("--max-price", type=float, help="Maximum player cost (e.g., 10.0).")
    parser.add_argument("--rising", action="store_true", help="Return players at or above --threshold on the selected metric.")
    parser.add_argument("--falling", action="store_true", help="Return players at or below negative --threshold on the selected metric.")
    parser.add_argument("--threshold", type=float, default=100.0, help="Threshold percentage for --rising/--falling. Default: 100.0.")
    parser.add_argument("--min-percent", type=float, help="Minimum selected metric percentage.")
    parser.add_argument("--max-percent", type=float, help="Maximum selected metric percentage.")
    parser.add_argument("--metric", choices=["current", "projected", "both"], default="projected", help="Metric to filter: current, projected, or both. Default: projected.")
    parser.add_argument("--projection-offset", type=int, default=0, help="Projection offset to read from price_change_projections. Default: 0.")
    parser.add_argument("--limit", type=int, default=MAX_PLAYERS, help=f"Maximum players to return in one page (1-{MAX_PLAYERS}; default: {MAX_PLAYERS}).")
    parser.add_argument("--offset", type=int, default=0, help="Zero-based offset for bounded pagination (default: 0).")
    parser.add_argument("--force-refresh", action="store_true", help="Force fetching fresh data from the API, ignoring cache.")
    args = parser.parse_args()

    if not 1 <= args.limit <= MAX_PLAYERS:
        parser.error(f"--limit must be between 1 and {MAX_PLAYERS}")
    if args.offset < 0:
        parser.error("--offset must be zero or greater")

    player_filters_active = any([
        args.player is not None,
        args.player_ids is not None,
        args.team is not None,
        args.team_id is not None,
        args.position is not None,
        args.min_price is not None,
        args.max_price is not None,
    ])
    price_filters_active = any([
        args.rising,
        args.falling,
        args.min_percent is not None,
        args.max_percent is not None,
    ])
    if not player_filters_active and not price_filters_active:
        msg = "No specific data requested. Use --rising, --falling, --min-percent/--max-percent, or player filters like --player, --team, --position."
        print(format_json_output(status="info", message=msg))
        return

    try:
        data = FPLUtils().fetch_url_cached(BASE_URL, "bootstrap_static", args.force_refresh)
    except Exception as exc:
        print(format_json_output(status="error", message=f"Failed to load FPL price-change data: {exc}"))
        return

    filter_team_id, team_filter_message, team_filter_error = resolve_team_id(data, args.team, args.team_id)
    if team_filter_error:
        print(format_json_output(status="error", message=team_filter_error))
        return

    players = filter_players(
        data=data,
        name=args.player,
        player_ids=args.player_ids,
        team_id=filter_team_id,
        position=args.position,
        min_price=args.min_price,
        max_price=args.max_price,
        projection_offset=args.projection_offset,
    )

    if price_filters_active:
        players = apply_price_filters(players, args)

    if args.rising and not args.falling:
        players.sort(key=lambda player: selected_sort_value(player, args.metric), reverse=True)
    elif args.falling and not args.rising:
        players.sort(key=lambda player: selected_sort_value(player, args.metric))
    else:
        players.sort(key=lambda player: abs(selected_sort_value(player, args.metric)), reverse=True)

    output_data: Dict[str, Any] = {
        "player_count": len(players),
        "metric": args.metric,
        "projection_offset": args.projection_offset,
    }
    if team_filter_message:
        output_data["team_filter_info"] = team_filter_message

    page_end = min(args.offset + args.limit, len(players))
    page_players = players[args.offset:page_end]
    has_more = page_end < len(players)
    output_data["players"] = page_players
    output_data["returned_count"] = len(page_players)
    output_data["offset"] = args.offset
    output_data["limit"] = args.limit
    output_data["has_more"] = has_more
    output_data["next_offset"] = page_end if has_more else None
    output_data["limit_hit"] = has_more
    if has_more:
        output_data["limit_message"] = (
            f"This query matched {len(players)} players. Returned the bounded page at offset {args.offset} "
            f"with limit {args.limit}; use --offset {page_end} for the next page, or narrow the filters."
        )

    print(format_json_output(status="success", data=output_data))


if __name__ == "__main__":
    main()
