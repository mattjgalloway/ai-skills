import json
import os
import re
from datetime import datetime, date
from urllib import request, error
from typing import Any, Dict, Optional

class StatsTracker:
    """Simple JSON-backed tracker for per-URL stats (requests, api_fetches)."""
    def __init__(self, cache_dir: str, filename: str = "fpl_cache_stats.json") -> None:
        self.filepath = os.path.join(cache_dir, filename)
        self._data: Dict[str, Dict[str, int]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self) -> None:
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def increment_request(self, url: str) -> None:
        entry = self._data.get(url, {"requests": 0, "api_fetches": 0})
        entry["requests"] = entry.get("requests", 0) + 1
        self._data[url] = entry
        self._save()

    def increment_api_fetch(self, url: str) -> None:
        entry = self._data.get(url, {"requests": 0, "api_fetches": 0})
        entry["api_fetches"] = entry.get("api_fetches", 0) + 1
        self._data[url] = entry
        self._save()


class LiveFPLUtils:
    cache_dir: str
    cache_expiry_days: int

    def __init__(self, cache_dir: str = "cache", cache_expiry_hours: int = 12) -> None:
        if not os.path.isabs(cache_dir):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(base_dir, cache_dir)
        self.cache_dir = cache_dir
        # expiry in hours (default 12)
        self.cache_expiry_hours = cache_expiry_hours
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        self.stats = StatsTracker(self.cache_dir)

    def _parse_prices_html(self, html: str) -> Dict[str, Any]:
        """Extracts player price progress info from HTML.

        Returns a dict with a list of players: {"players": [{"id": int, "now": float_or_none, "tonight": float_or_none}, ...]}
        """
        players = []
        # Find all div tags containing data-id; keep the tag text to extract attributes
        # Match attributes allowing optional spaces around '=' and either single/double quotes
        for m in re.finditer(r"<div[^>]*data-id\s*=\s*['\"]?(?P<id>\d+)['\"]?[^>]*>", html, re.IGNORECASE):
            tag_text = m.group(0)
            pid = int(m.group('id'))
            now = None
            tonight = None
            now_m = re.search(r'data-now\s*=\s*["\']?([^"\'>\s]+)["\']?', tag_text)
            if now_m:
                try:
                    now = float(now_m.group(1))
                except Exception:
                    now = None
            tonight_m = re.search(r'data-tonight\s*=\s*["\']?([^"\'>\s]+)["\']?', tag_text)
            if tonight_m:
                try:
                    tonight = float(tonight_m.group(1))
                except Exception:
                    tonight = None
            players.append({"id": pid, "pct_now": now, "pct_tonight": tonight})

        # In some pages attributes may be on the same line but not in the opening div; try a broader approach
        if not players:
            # generic attribute extraction across the HTML
            for m in re.finditer(r'data-id\s*=\s*["\']?(\d+)["\']?', html):
                pid = int(m.group(1))
                # search within a short window after the match to find the attributes
                start = m.start()
                window = html[start:start+300]
                now = None
                tonight = None
                now_m = re.search(r'data-now\s*=\s*["\']?([^"\'>\s]+)["\']?', window)
                tonight_m = re.search(r'data-tonight\s*=\s*["\']?([^"\'>\s]+)["\']?', window)
                if now_m:
                    try:
                        now = float(now_m.group(1))
                    except Exception:
                        now = None
                if tonight_m:
                    try:
                        tonight = float(tonight_m.group(1))
                    except Exception:
                        tonight = None
                players.append({"id": pid, "pct_now": now, "pct_tonight": tonight})

        # Deduplicate by player id while preserving first-seen order
        unique_players: Dict[int, Dict[str, Any]] = {}
        for p in players:
            pid = p.get('id')
            if pid is None:
                continue
            if pid not in unique_players:
                unique_players[pid] = p

        deduped = list(unique_players.values())
        return {"players": deduped, "fetched_at": datetime.utcnow().isoformat() + 'Z'}

    def fetch_prices_cached(self, url: str, cache_key: str, force_refresh: bool) -> Dict[str, Any]:
        # Cache the raw HTML so subsequent runs can re-parse and filter without refetching
        html_cache_path = os.path.join(self.cache_dir, f"fpl_cache_{cache_key}.html")
        try:
            self.stats.increment_request(url)
        except Exception:
            pass
        # Try cache (HTML) — check modification time against expiry in hours
        if not force_refresh and os.path.exists(html_cache_path):
            file_mod_timestamp = os.path.getmtime(html_cache_path)
            file_mod_dt = datetime.fromtimestamp(file_mod_timestamp)
            age_seconds = (datetime.utcnow() - file_mod_dt).total_seconds()
            if age_seconds < (self.cache_expiry_hours * 3600):
                try:
                    with open(html_cache_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                        return self._parse_prices_html(html)
                except Exception:
                    pass

        # Fetch HTML from remote
        try:
            with request.urlopen(url) as response:
                if response.getcode() != 200:
                    raise error.HTTPError(url, response.getcode(), f"HTTP Error {response.getcode()}", response.info(), None)
                html_bytes = response.read()
                html = html_bytes.decode('utf-8', errors='ignore')

            # Save raw HTML to cache for later filtering
            try:
                with open(html_cache_path, 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception:
                pass

            try:
                self.stats.increment_api_fetch(url)
            except Exception:
                pass

            return self._parse_prices_html(html)
        except error.URLError as e:
            raise Exception(f"Network Error fetching {cache_key} from {url}: {e.reason}")
        except error.HTTPError as e:
            raise Exception(f"API Error fetching {cache_key} from {url}: Status {e.code}, Reason {e.reason}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during {cache_key} fetch from {url}: {e}")


def format_json_output(status: str, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> str:
    output = {"status": status}
    if message:
        output["message"] = message
    if data is not None:
        output["data"] = data
    return json.dumps(output, indent=2)
