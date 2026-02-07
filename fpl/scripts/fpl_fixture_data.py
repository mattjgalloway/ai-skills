import argparse
from typing import Any, Dict, List, Optional
from fpl_utils import FPLUtils, format_json_output

class FPLFixtureData:
    BASE_URL: str = "https://fantasy.premierleague.com/api/fixtures/"

    def __init__(self, fpl_utils: FPLUtils) -> None:
        self.fpl_utils: FPLUtils = fpl_utils

    def _load_data(self, force_refresh: bool = False, gameweek: Optional[int] = None) -> Any:
        cache_key = f"fixtures_event_{gameweek}" if gameweek is not None else "fixtures"
        url = self.BASE_URL
        if gameweek is not None:
            url = f"{self.BASE_URL}?event={gameweek}"
        return self.fpl_utils.fetch_url_cached(url, cache_key, force_refresh)

    def get_fixtures(self, gameweek: Optional[int] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        data = self._load_data(force_refresh=force_refresh, gameweek=gameweek)
        # API returns a list of fixture objects for this endpoint
        fixtures = data if isinstance(data, list) else []

        return [{
            'id': f.get('id'),
            'event': f.get('event'),
            'team_h': f.get('team_h'),
            'team_a': f.get('team_a'),
            'team_h_difficulty': f.get('team_h_difficulty'),
            'team_a_difficulty': f.get('team_a_difficulty'),
            'minutes': f.get('minutes'),
            'started': f.get('started'),
            'finished': f.get('finished'),
            'kickoff_time': f.get('kickoff_time'),
            'team_h_score': f.get('team_h_score'),
            'team_a_score': f.get('team_a_score'),
            'score': (f"{f.get('team_h_score')}-{f.get('team_a_score')}" if f.get('team_h_score') is not None and f.get('team_a_score') is not None else None)
        } for f in fixtures]


def main():
    parser = argparse.ArgumentParser(description="Fetch Fantasy Premier League fixtures data.")
    parser.add_argument('--fixtures', action='store_true', help='Show all fixtures.')
    parser.add_argument('--gameweek', type=int, help='Fetch fixtures for a specific gameweek (integer).')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the API, ignoring cache.')

    args = parser.parse_args()

    fpl_utils = FPLUtils()
    fixture_fetcher = FPLFixtureData(fpl_utils)

    output_status = "success"
    output_data = {}
    output_message = None

    try:
        if args.fixtures:
            output_data['fixtures'] = fixture_fetcher.get_fixtures(force_refresh=args.force_refresh)
        elif args.gameweek is not None:
            output_data['fixtures'] = fixture_fetcher.get_fixtures(gameweek=args.gameweek, force_refresh=args.force_refresh)
        else:
            output_status = "info"
            output_message = "No specific data requested. Use --fixtures or --gameweek <n>."
    except Exception as e:
        output_status = "error"
        output_message = f"Failed to fetch fixtures: {e}"

    print(format_json_output(status=output_status, data=output_data, message=output_message))

if __name__ == "__main__":
    main()
