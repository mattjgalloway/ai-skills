import argparse
from typing import Any, Dict, List
from fpl_utils import FPLUtils, format_json_output


class FPLLeagueStandings:
    BASE_URL_TEMPLATE: str = "https://fantasy.premierleague.com/api/leagues-classic/{lid}/standings/?page_standings={page}"

    def __init__(self, fpl_utils: FPLUtils) -> None:
        self.fpl_utils: FPLUtils = fpl_utils

    def _load_data(self, league_id: int, page: int = 1, force_refresh: bool = False) -> Any:
        url = self.BASE_URL_TEMPLATE.format(lid=league_id, page=page)
        cache_key = f"league_{league_id}_standings_p{page}"
        return self.fpl_utils.fetch_url_cached(url, cache_key, force_refresh)

    def get_standings(self, league_id: int, page: int = 1, force_refresh: bool = False) -> Dict[str, Any]:
        """Return a dict with `league` details and `standings` list for the requested page.

        The returned structure is:
          {
            'league': { ... },
            'standings': [ {entry fields}, ... ],
            'page': { 'page': N, 'results': M, 'has_next': bool, 'has_previous': bool }
          }
        """
        data = self._load_data(league_id, page, force_refresh)
        if not isinstance(data, dict):
            return {'league': {}, 'standings': [], 'page': {'page': page, 'results': 0, 'has_next': None, 'has_previous': None}}

        league = data.get('league', {})
        standings_section = data.get('standings', {})
        results = standings_section.get('results', []) if isinstance(standings_section, dict) else []

        standings = []
        for r in results:
            standings.append({
                'rank': r.get('rank'),
                'entry': r.get('entry'),
                'player_name': r.get('player_name'),
                'entry_name': r.get('entry_name'),
                'total': r.get('total'),
                'event_total': r.get('event_total'),
                'last_rank': r.get('last_rank'),
                'movement': r.get('movement')
            })

        page_info = {
            'page': standings_section.get('page') if isinstance(standings_section, dict) else page,
            'results': len(results),
            'has_next': standings_section.get('has_next') if isinstance(standings_section, dict) else None,
            'has_previous': standings_section.get('has_previous') if isinstance(standings_section, dict) else None
        }

        return {'league': league, 'standings': standings, 'page': page_info}


def main():
    parser = argparse.ArgumentParser(description='Fetch league standings for a given Classic league ID.')
    parser.add_argument('league_id', type=int, help='League ID (classic league).')
    parser.add_argument('--page', type=int, default=1, help='Page of standings to fetch (default 1).')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the API, ignoring cache.')

    args = parser.parse_args()

    fpl_utils = FPLUtils()
    fetcher = FPLLeagueStandings(fpl_utils)

    output_status = 'success'
    output_data = {}
    output_message = None

    try:
        output_data = fetcher.get_standings(args.league_id, page=args.page, force_refresh=args.force_refresh)
    except Exception as e:
        output_status = 'error'
        output_message = f'Failed to fetch league standings: {e}'

    print(format_json_output(status=output_status, data=output_data, message=output_message))


if __name__ == '__main__':
    main()
