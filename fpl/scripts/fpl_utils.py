import json
import os
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


class FPLUtils:
    cache_dir: str
    cache_expiry_days: int

    def __init__(self, cache_dir: str = "cache", cache_expiry_days: int = 1) -> None:
        # If a relative path is provided, interpret it relative to this script's directory
        if not os.path.isabs(cache_dir):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(base_dir, cache_dir)
        self.cache_dir = cache_dir
        self.cache_expiry_days = cache_expiry_days
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        # Stats tracker for URL request counting
        self.stats = StatsTracker(self.cache_dir)

    def fetch_url_cached(self, url: str, cache_key: str, force_refresh: bool) -> Dict[str, Any]:
        """
        Fetches data from a given URL, using a cache file if available and valid.

        Args:
            url (str): The URL to fetch data from.
            cache_key (str): A unique identifier for the cache file (e.g., "bootstrap_static", "entry_123_details").
            force_refresh (bool): If True, forces a fresh fetch from the URL, ignoring cache.

        Returns:
            dict: The JSON data from the URL or cache.

        Raises:
            Exception: If a network, API, or data parsing error occurs.
        """
        cache_file_path = os.path.join(self.cache_dir, f"fpl_cache_{cache_key}.json")

        # Update simple stats: count this request invocation (non-fatal)
        try:
            self.stats.increment_request(url)
        except Exception:
            pass

        # Try to load from cache
        if not force_refresh and os.path.exists(cache_file_path):
            file_mod_timestamp = os.path.getmtime(cache_file_path)
            file_mod_date = datetime.fromtimestamp(file_mod_timestamp).date()
            if (date.today() - file_mod_date).days < self.cache_expiry_days:
                try:
                    with open(cache_file_path, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass  # Cache corrupted, will proceed to fetch fresh data
                except Exception:
                    pass  # Other cache read error, will proceed to fetch fresh data

        # Fetch from API if cache failed or not used
        try:
            with request.urlopen(url) as response:
                if response.getcode()!= 200:
                    raise error.HTTPError(url, response.getcode(), f"HTTP Error {response.getcode()}: {response.reason}", response.info(), None)
                data_bytes = response.read()
                data = json.loads(data_bytes.decode('utf-8'))

            # Save to cache
            with open(cache_file_path, 'w') as f:
                json.dump(data, f, indent=4)
            # Record that we actually fetched from the API (non-fatal)
            try:
                self.stats.increment_api_fetch(url)
            except Exception:
                pass
            return data
        except error.URLError as e:
            raise Exception(f"Network Error fetching {cache_key} from {url}: {e.reason}")
        except error.HTTPError as e:
            raise Exception(f"API Error fetching {cache_key} from {url}: Status {e.code}, Reason {e.reason}")
        except json.JSONDecodeError as e:
            raise Exception(f"Data Parsing Error fetching {cache_key} from {url}: Failed to decode JSON. Error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during {cache_key} fetch from {url}: {e}")


def format_json_output(status: str, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> str:
    """
    Standardizes the JSON output format for both FPL scripts.

    Args:
        status (str): The status of the operation (e.g., "success", "error", "info").
        data (dict, optional): The data payload. Defaults to None.
        message (str, optional): A descriptive message. Defaults to None.

    Returns:
        str: A JSON formatted string.
    """
    output = {"status": status}
    if message:
        output["message"] = message
    # Include `data` even when it's an empty dict/list; only omit when None
    if data is not None:
        output["data"] = data
    return json.dumps(output, indent=2)
