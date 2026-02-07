import argparse
from fpl_utils import FPLUtils, format_json_output

class FPLLiveGameweek:
    BASE_URL_TEMPLATE = "https://fantasy.premierleague.com/api/event/{gw}/live/"

    def __init__(self, fpl_utils: FPLUtils):
        self.fpl_utils = fpl_utils

    def _load_data(self, gameweek: int, force_refresh=False):
        """Load live data for the given gameweek (required).

        Args:
            gameweek (int): Gameweek number to load.
            force_refresh (bool): If True, bypass cache.

        Returns:
            tuple: (data, gameweek)
        """
        url = self.BASE_URL_TEMPLATE.format(gw=gameweek)
        cache_key = f"live_event_{gameweek}"
        return self.fpl_utils.fetch_url_cached(url, cache_key, force_refresh), gameweek

    def get_live_gameweek(self, gameweek: int, player_ids=None, force_refresh=False):
        data, resolved_gw = self._load_data(gameweek, force_refresh=force_refresh)
        # The live endpoint typically returns a dict with 'elements' and 'events'
        if not isinstance(data, dict):
            return {'gameweek': resolved_gw, 'elements': [], 'events': []}

        elements = data.get('elements', [])
        events = data.get('events', [])

        formatted_elements = []
        for e in elements:
            eid = e.get('id')
            # Apply optional player filtering using a list of ids (single-element lists supported)
            if player_ids is not None and eid not in player_ids:
                continue
            formatted_elements.append({
                'id': eid,
                'stats': e.get('stats', {}),
                'explain': e.get('explain', [])
            })

        formatted_events = []
        for ev in events:
            formatted_events.append({
                'id': ev.get('id'),
                'stats': ev.get('stats', {})
            })

        return {
            'gameweek': resolved_gw,
            'elements': formatted_elements,
            'events': formatted_events
        }


def main():
    parser = argparse.ArgumentParser(description="Fetch live gameweek data from FPL API.")
    parser.add_argument('--gameweek', type=int, required=True, help='Fetch live data for a specific gameweek (integer).')
    parser.add_argument('--player-ids', type=int, nargs='+', required=True, help='Filter output to one or more player IDs (space-separated).')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the API, ignoring cache.')

    args = parser.parse_args()

    fpl_utils = FPLUtils()
    live_fetcher = FPLLiveGameweek(fpl_utils)

    output_status = "success"
    output_data = {}
    output_message = None

    try:
        output_data['live'] = live_fetcher.get_live_gameweek(
            gameweek=args.gameweek,
            player_ids=args.player_ids,
            force_refresh=args.force_refresh
        )
    except Exception as e:
        output_status = "error"
        output_message = f"Failed to fetch live gameweek data: {e}"

    print(format_json_output(status=output_status, data=output_data, message=output_message))

if __name__ == "__main__":
    main()
