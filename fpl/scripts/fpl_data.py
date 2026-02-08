import argparse
import unicodedata
from typing import Any, Dict, List, Optional
from fpl_utils import FPLUtils, format_json_output  # Import the utility and formatter


def normalize_str(s: Optional[str]) -> str:
    """Return a lower-cased, accent-stripped ascii representation of s for comparison."""
    if s is None:
        return ''
    # Decompose unicode characters and remove combining diacritics
    normalized = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in normalized if not unicodedata.combining(c)).lower()


class FPLData:
    BASE_URL: str = "https://fantasy.premierleague.com/api/bootstrap-static/"

    def __init__(self, fpl_utils: FPLUtils) -> None:
        self.fpl_utils: FPLUtils = fpl_utils
        self._data: Optional[Dict[str, Any]] = None
        self.team_name_map: Dict[int, str] = {}
        self.position_map: Dict[Any, Any] = {}

    def _load_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Loads data from API or cache using FPLUtils."""
        if self._data is None or force_refresh:
            try:
                self._data = self.fpl_utils.fetch_url_cached(self.BASE_URL, "bootstrap_static", force_refresh)
                self._build_team_map()
                self._build_position_map()
            except Exception as e:
                # Store the error message in _data for main to retrieve and format
                self._data = {"error": str(e)} 
                raise # Re-raise to be caught by main() for JSON error output
        return self._data

    def _build_team_map(self) -> None:
        if self._data and 'teams' in self._data:
            self.team_name_map = {team.get('id'): team.get('name') for team in self._data.get('teams', [])}

    def _build_position_map(self) -> None:
        if self._data and 'element_types' in self._data:
            self.position_map = {et.get('id'): et.get('singular_name_short') for et in self._data.get('element_types', [])}
            for et in self._data.get('element_types', []):
                if et.get('singular_name'):
                    self.position_map[et['singular_name'].lower()] = et['id']
                if et.get('plural_name_short'):
                    self.position_map[et['plural_name_short'].lower()] = et['id']

    def get_teams(self) -> List[Dict[str, Any]]:
        data = self._data 
        teams = data.get('teams', [])
        return [{
            'id': team.get('id'),
            'name': team.get('name'),
            'short_name': team.get('short_name'),
            'strength': team.get('strength')
        } for team in teams]

    def get_players(self, name: Optional[str] = None, player_ids: Optional[List[int]] = None, team_id: Optional[int] = None, position: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        data = self._data 
        elements = data.get('elements', [])

        player_details = []
        for player in elements:
            player_now_cost = player.get('now_cost')
            player_cost = player_now_cost / 10.0 if player_now_cost is not None else None

            player_first_name = player.get('first_name', '')
            player_second_name = player.get('second_name', '')
            full_name = f"{player_first_name} {player_second_name}".strip()

            player_team_id = player.get('team')
            player_element_type = player.get('element_type')

            player_info = {
                'id': player.get('id'),
                'first_name': player_first_name,
                'second_name': player_second_name,
                'full_name': full_name,
                'team_id': player_team_id,
                'team_name': self.team_name_map.get(player_team_id, 'Unknown Team'),
                'total_points': player.get('total_points'),
                'points_this_gameweek': player.get('event_points'),
                'element_type': player_element_type,
                'position': self.position_map.get(player_element_type, 'Unknown'),
                'now_cost': player_cost,
                'status': player.get('status'),
                'selected_by_percent': player.get('selected_by_percent')
            }

            if name and normalize_str(name) not in normalize_str(full_name):
                continue
            if player_ids is not None and player_info['id'] not in player_ids:
                continue
            if team_id is not None and team_id != player_team_id:
                continue
            if position:
                target_position_id = self.position_map.get(position.lower())
                if target_position_id is None or target_position_id != player_element_type:
                    continue
            if min_price is not None and (player_cost is None or player_cost < min_price):
                continue
            if max_price is not None and (player_cost is None or player_cost > max_price):
                continue

            player_details.append(player_info)
        return player_details

    def get_gameweeks(self) -> List[Dict[str, Any]]:
        data = self._data
        events = data.get('events', [])
        return [{
            'id': event.get('id'),
            'name': event.get('name'),
            'deadline_time': event.get('deadline_time'),
            'average_score': event.get('average_entry_score'),
            'finished': event.get('finished'),
            'is_current': event.get('is_current'),
            'is_next': event.get('is_next'),
            'most_selected_player_id': event.get('most_selected'),
            'top_element_id': event.get('top_element'),
            'top_element_points': (event.get('top_element_info') or {}).get('points')
        } for event in events]


def main():
    parser = argparse.ArgumentParser(description="Fetch and display Fantasy Premier League data.")
    parser.add_argument('--gameweeks', action='store_true', help='Show details for all gameweeks.')
    parser.add_argument('--teams', action='store_true', help='Show details for all teams.')
    parser.add_argument('--team', type=str, help='Filter players by team name (case-insensitive, partial match).')
    parser.add_argument('--team-id', type=int, help='Filter players by team ID.')
    parser.add_argument('--player', type=str, help='Filter players by player name (case-insensitive, partial match).')
    parser.add_argument('--player-ids', type=int, nargs='+', help='Filter players by multiple player IDs (space-separated).')
    parser.add_argument('--position', type=str, help='Filter players by position (GKP, DEF, MID, FWD).')
    parser.add_argument('--min-price', type=float, help='Minimum player cost (e.g., 4.5).')
    parser.add_argument('--max-price', type=float, help='Maximum player cost (e.g., 10.0).')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the API, ignoring cache.')

    args = parser.parse_args()

    fpl_utils = FPLUtils()
    fpl = FPLData(fpl_utils)
    output_data = {}
    output_message = None
    output_status = "success"

    try:
        fpl._load_data(force_refresh=args.force_refresh)
    except Exception as e:
        output_status = "error"
        output_message = f"Failed to load FPL general data: {e}"
        print(format_json_output(status=output_status, message=output_message))
        return

    if not fpl._data or "error" in fpl._data: # Check if _data contains an error from _load_data
        output_status = "error"
        output_message = fpl._data.get("error", "Could not load FPL general data from API or cache.")
        print(format_json_output(status=output_status, message=output_message))
        return

    filter_team_id = args.team_id
    team_filter_message = None
    if args.team:
        all_teams = fpl.get_teams()
        search_team = normalize_str(args.team)
        found_teams = [team['id'] for team in all_teams if search_team in normalize_str(team.get('name')) or search_team in normalize_str(team.get('short_name'))]
        if len(found_teams) == 1:
            if filter_team_id is not None and filter_team_id != found_teams[0]:
                team_filter_message = f"Warning: Both --team '{args.team}' (ID {found_teams[0]}) and --team-id '{args.team_id}' were provided and conflict. Using --team-id: {args.team_id}."
            else:
                filter_team_id = found_teams[0]
            if not team_filter_message:
                team_filter_message = f"Filtering by team name: '{args.team}' (Resolved to ID: {filter_team_id})"
        elif len(found_teams) > 1:
            output_status = "error"
            output_message = f"Multiple teams found for '{args.team}': {[fpl.team_name_map.get(tid) for tid in found_teams]}. Please be more specific or use the team ID with --team-id."
            print(format_json_output(status=output_status, message=output_message))
            return
        elif not filter_team_id:
            output_status = "error"
            output_message = f"No team found matching '{args.team}'. Please check the name."
            print(format_json_output(status=output_status, message=output_message))
            return
    elif args.team_id is not None:
        team_filter_message = f"Filtering by team ID: {args.team_id}"

    if team_filter_message:
        output_data["team_filter_info"] = team_filter_message

    if args.gameweeks:
        output_data["gameweeks"] = fpl.get_gameweeks()

    if args.teams:
        output_data["teams"] = fpl.get_teams()

    specific_player_filters_active = (args.player is not None or
                                      args.player_ids is not None or args.position is not None or args.min_price is not None or
                                      args.max_price is not None or args.team is not None or args.team_id is not None)

    if specific_player_filters_active:
        filtered_players = fpl.get_players(
            name=args.player,
            player_ids=args.player_ids,
            team_id=filter_team_id,
            position=args.position,
            min_price=args.min_price,
            max_price=args.max_price
        )
        output_data["player_count"] = len(filtered_players)
        output_data["players"] = filtered_players

    if not (args.gameweeks or args.teams or specific_player_filters_active):
        output_status = "info"
        output_message = "No specific data requested. Use --gameweeks, --teams, or filters like --player, --team, etc."

    print(format_json_output(status=output_status, data=output_data, message=output_message))


if __name__ == "__main__":
    main()