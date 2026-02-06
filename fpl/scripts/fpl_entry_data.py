import argparse
import json
import os
from fpl_utils import FPLUtils, format_json_output # Import the utility and formatter

class FPLEntryData:
    BASE_URL = "https://fantasy.premierleague.com/api/entry/"

    def __init__(self, entry_id: int, fpl_utils: FPLUtils):
        self.entry_id = entry_id
        self.fpl_utils = fpl_utils # Use the shared utility
        # These will store raw fetched data for processing
        self._raw_details_data = None
        self._raw_history_data = None
        self._raw_transfers_data = None
        self._raw_picks_data = {} # Store picks data per gameweek

    def get_entry_details(self, force_refresh: bool = False):
        url = f"{self.BASE_URL}{self.entry_id}/"
        try:
            self._raw_details_data = self.fpl_utils.fetch_url_cached(url, f"entry_{self.entry_id}_details", force_refresh)
            
            leagues = {
                "classic": [{"id": l.get('id'), "name": l.get('name'), "entry_rank": l.get('entry_rank'), "entry_last_rank": l.get('entry_last_rank')} for l in self._raw_details_data.get('leagues', {}).get('classic', [])],
                "h2h": [{"id": l.get('id'), "name": l.get('name'), "entry_rank": l.get('entry_rank'), "entry_last_rank": l.get('entry_last_rank')} for l in self._raw_details_data.get('leagues', {}).get('h2h', [])]
            }

            return {
                "id": self._raw_details_data.get('id'),
                "team_name": self._raw_details_data.get('name'),
                "manager_first_name": self._raw_details_data.get('player_first_name'),
                "manager_last_name": self._raw_details_data.get('player_last_name'),
                "player_region_name": self._raw_details_data.get('player_region_name'),
                "overall_points": self._raw_details_data.get('summary_overall_points'),
                "overall_rank": self._raw_details_data.get('summary_overall_rank'),
                "event_points": self._raw_details_data.get('summary_event_points'),
                "event_rank": self._raw_details_data.get('summary_event_rank'),
                "current_gameweek": self._raw_details_data.get('current_event'),
                "leagues": leagues,
                "years_active": self._raw_details_data.get('years_active')
            }
        except Exception as e:
            raise Exception(f"Failed to get entry details for ID {self.entry_id}: {e}")

    def get_history(self, force_refresh: bool = False):
        url = f"{self.BASE_URL}{self.entry_id}/history/"
        try:
            self._raw_history_data = self.fpl_utils.fetch_url_cached(url, f"entry_{self.entry_id}_history", force_refresh)
            
            current_season_history = []
            for gw_data in self._raw_history_data.get('current', []):
                current_season_history.append({
                    "gameweek": gw_data.get('event'),
                    "points": gw_data.get('points'),
                    "total_points": gw_data.get('total_points'),
                    "overall_rank": gw_data.get('overall_rank'),
                    "gameweek_rank": gw_data.get('rank'),
                    "transfers_made": gw_data.get('event_transfers'),
                    "transfers_cost": gw_data.get('event_transfers_cost'),
                    "points_on_bench": gw_data.get('points_on_bench'),
                    "team_value": gw_data.get('value') / 10.0,
                    "bank": gw_data.get('bank') / 10.0
                })

            past_seasons_history = []
            for season_data in self._raw_history_data.get('past', []):
                past_seasons_history.append({
                    "season_name": season_data.get('season_name'),
                    "total_points": season_data.get('total_points'),
                    "overall_rank": season_data.get('rank')
                })

            chips_played = []
            for chip_data in self._raw_history_data.get('chips', []):
                chips_played.append({
                    "name": chip_data.get('name'),
                    "gameweek": chip_data.get('event'),
                    "time_played": chip_data.get('time')
                })

            return {
                "current_season_history": current_season_history,
                "past_seasons_history": past_seasons_history,
                "chips_played": chips_played
            }

        except Exception as e:
            raise Exception(f"Failed to get history for entry ID {self.entry_id}: {e}")

    def get_transfers(self, force_refresh: bool = False):
        url = f"{self.BASE_URL}{self.entry_id}/transfers/"
        try:
            self._raw_transfers_data = self.fpl_utils.fetch_url_cached(url, f"entry_{self.entry_id}_transfers", force_refresh)
            
            transfers_list = []
            for transfer in self._raw_transfers_data:
                transfers_list.append({
                    "gameweek": transfer.get('event'),
                    "time": transfer.get('time'),
                    "element_in_id": transfer.get('element_in'),
                    "element_in_cost": transfer.get('element_in_cost') / 10.0,
                    "element_out_id": transfer.get('element_out'),
                    "element_out_cost": transfer.get('element_out_cost') / 10.0,
                })
            return transfers_list

        except Exception as e:
            raise Exception(f"Failed to get transfers for entry ID {self.entry_id}: {e}")

    def get_picks(self, gameweek: int, force_refresh: bool = False):
        url = f"{self.BASE_URL}{self.entry_id}/event/{gameweek}/picks/"
        try:
            self._raw_picks_data[gameweek] = self.fpl_utils.fetch_url_cached(url, f"entry_{self.entry_id}_picks_gw{gameweek}", force_refresh)
            raw_data = self._raw_picks_data[gameweek]

            picks_data = []
            for pick in raw_data.get('picks', []):
                picks_data.append({
                    "element_id": pick.get('element'),
                    "position": pick.get('position'),
                    "multiplier": pick.get('multiplier'),
                    "is_captain": pick.get('is_captain'),
                    "is_vice_captain": pick.get('is_vice_captain'),
                    "element_type": pick.get('element_type')
                })
            
            automatic_subs = []
            for sub in raw_data.get('automatic_subs', []):
                automatic_subs.append({
                    "element_in_id": sub.get('element_in'),
                    "element_out_id": sub.get('element_out'),
                    "gameweek": sub.get('event')
                })

            return {
                "gameweek": gameweek,
                "active_chip": raw_data.get('active_chip'),
                "entry_history_summary": {
                    "event_points": raw_data.get('entry_history', {}).get('points'),
                    "total_points": raw_data.get('entry_history', {}).get('total_points'),
                    "overall_rank": raw_data.get('entry_history', {}).get('overall_rank')
                },
                "picks": picks_data,
                "automatic_substitutions": automatic_subs
            }

        except Exception as e:
            raise Exception(f"Failed to get picks for entry ID {self.entry_id}, Gameweek {gameweek}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Fetch and display Fantasy Premier League entry data for a given team ID.")
    parser.add_argument('entry_id', type=int, help='The FPL team ID for which to fetch data.')
    parser.add_argument('--details', action='store_true', help='Get general details about the FPL entry (team name, manager, overall points/rank, leagues, etc.).')
    parser.add_argument('--history', action='store_true', help='Get historical performance data for the FPL entry (gameweek points, overall ranks, past seasons, chips played).')
    parser.add_argument('--transfers', action='store_true', help='Get player transfer history for the FPL entry.')
    parser.add_argument('--picks', type=int, metavar='GAMEWEEK_NUMBER', help='Get player picks for a specific gameweek. Requires GAMEWEEK_NUMBER.')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the API, ignoring cache.')
    
    args = parser.parse_args()

    fpl_utils = FPLUtils() # Initialize the utility
    entry_data_fetcher = FPLEntryData(entry_id=args.entry_id, fpl_utils=fpl_utils)
    output_data = {}
    output_message = None
    output_status = "success"

    try:
        if args.details:
            output_data["entry_details"] = entry_data_fetcher.get_entry_details(force_refresh=args.force_refresh)
        
        if args.history:
            output_data["entry_history"] = entry_data_fetcher.get_history(force_refresh=args.force_refresh)

        if args.transfers:
            output_data["entry_transfers"] = entry_data_fetcher.get_transfers(force_refresh=args.force_refresh)

        if args.picks:
            output_data["entry_picks"] = entry_data_fetcher.get_picks(gameweek=args.picks, force_refresh=args.force_refresh)
        
        if not (args.details or args.history or args.transfers or args.picks):
            output_status = "info"
            output_message = f"No specific data type requested for entry ID {args.entry_id}. Use --details, --history, --transfers, or --picks <GAMEWEEK_NUMBER>."

    except Exception as e:
        output_status = "error"
        output_message = str(e)

    print(format_json_output(status=output_status, data=output_data, message=output_message))

if __name__ == "__main__":
    main()