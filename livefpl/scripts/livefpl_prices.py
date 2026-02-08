import argparse
from livefpl_utils import LiveFPLUtils, format_json_output, MAX_PLAYERS

URL = "https://www.livefpl.net/prices"


def main():
    parser = argparse.ArgumentParser(description="Fetch LiveFPL prices progress and output cached JSON.")
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data from the website, ignoring cache.')
    parser.add_argument('--player-ids', type=int, nargs='+', help='Filter players by player IDs (space-separated).')
    parser.add_argument('--filter-gt', type=float, help='Numeric threshold: select metric >= value (use with --filter-now or --filter-tonight).')
    parser.add_argument('--filter-lt', type=float, help='Numeric threshold: select metric <= value (use with --filter-now or --filter-tonight).')
    parser.add_argument('--filter-now', action='store_true', help='Apply --filter-gt/--filter-lt to `pct_now`.')
    parser.add_argument('--filter-tonight', action='store_true', help='Apply --filter-gt/--filter-lt to `pct_tonight`.')
    args = parser.parse_args()

    utils = LiveFPLUtils()
    # Require at least one meaningful parameter (player filter or filter conditions)
    filter_flags = any([args.filter_now, args.filter_tonight, args.filter_gt is not None, args.filter_lt is not None])
    if not args.player_ids and not filter_flags:
        msg = "No specific data requested. Use --player-ids or filters: --filter-now/--filter-tonight with --filter-gt/--filter-lt."
        print(format_json_output(status='info', message=msg))
        return

    try:
        data = utils.fetch_prices_cached(URL, 'prices', force_refresh=args.force_refresh)
        players = data.get('players', [])

        # If player_ids provided, narrow to those first
        if args.player_ids:
            ids_set = set(args.player_ids)
            players = [p for p in players if p.get('id') in ids_set]

        # If any filter flags/thresholds provided, filter accordingly (logical OR across applied metrics)
        if filter_flags:
            out = []
            for p in players:
                pn = p.get('pct_now')
                pt = p.get('pct_tonight')
                keep = False

                # Apply filter to pct_now if requested
                if args.filter_now:
                    if args.filter_gt is not None and pn is not None and pn >= args.filter_gt:
                        keep = True
                    if args.filter_lt is not None and pn is not None and pn <= args.filter_lt:
                        keep = True

                # Apply filter to pct_tonight if requested
                if args.filter_tonight:
                    if args.filter_gt is not None and pt is not None and pt >= args.filter_gt:
                        keep = True
                    if args.filter_lt is not None and pt is not None and pt <= args.filter_lt:
                        keep = True

                # If neither specific metric flag given but thresholds provided, apply thresholds to both metrics
                if not args.filter_now and not args.filter_tonight:
                    if args.filter_gt is not None:
                        if pn is not None and pn >= args.filter_gt:
                            keep = True
                        if pt is not None and pt >= args.filter_gt:
                            keep = True
                    if args.filter_lt is not None:
                        if pn is not None and pn <= args.filter_lt:
                            keep = True
                        if pt is not None and pt <= args.filter_lt:
                            keep = True

                if keep:
                    out.append(p)
            players = out

        original_count = len(players)

        if original_count > MAX_PLAYERS:
            data['players'] = players[:MAX_PLAYERS]
            data['limit_hit'] = True
            data['limit_message'] = (
                f"Returned {original_count} players which exceeds the limit of {MAX_PLAYERS}. "
                "Please narrow the results using --player-ids or the --filter-* options to reduce the number of players returned."
            )
        else:
            data['players'] = players

        data['player_count'] = original_count
        print(format_json_output(status='success', data=data))
    except Exception as e:
        print(format_json_output(status='error', message=str(e)))


if __name__ == '__main__':
    main()
