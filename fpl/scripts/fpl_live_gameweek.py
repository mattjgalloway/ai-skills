import argparse
from typing import Any, Dict, List, Optional, Tuple
from fpl_utils import FPLUtils, format_json_output, MAX_PLAYERS


class FPLLiveGameweek:
    BASE_URL_TEMPLATE: str = "https://fantasy.premierleague.com/api/event/{gw}/live/"

    def __init__(self, fpl_utils: FPLUtils) -> None:
        self.fpl_utils: FPLUtils = fpl_utils

    def _load_data(self, gameweek: int, force_refresh: bool = False) -> Tuple[Dict[str, Any], int]:
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

    def get_live_gameweek(self, gameweek: int, player_ids: Optional[List[int]] = None, force_refresh: bool = False) -> Dict[str, Any]:
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

        # Enforce maximum elements returned to avoid huge outputs
        element_count = len(formatted_elements)
        result_elements = formatted_elements
        limit_hit = False
        limit_message = None
        if element_count > MAX_PLAYERS:
            result_elements = formatted_elements[:MAX_PLAYERS]
            limit_hit = True
            limit_message = (
                f"Returned {element_count} players which exceeds the limit of {MAX_PLAYERS}. "
                "Please narrow the results by providing fewer --player-ids or filtering on the caller side."
            )

        return {
            'gameweek': resolved_gw,
            'elements': result_elements,
            'element_count': element_count,
            'events': formatted_events,
            'limit_hit': limit_hit,
            'limit_message': limit_message
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
