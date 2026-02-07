import json
import os
from datetime import datetime, date
from urllib import request, error

class FPLUtils:
    def __init__(self, cache_dir="cache", cache_expiry_days=1):
        # If a relative path is provided, interpret it relative to this script's directory
        if not os.path.isabs(cache_dir):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cache_dir = os.path.join(base_dir, cache_dir)
        self.cache_dir = cache_dir
        self.cache_expiry_days = cache_expiry_days
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_url_cached(self, url: str, cache_key: str, force_refresh: bool):
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
        
        # Try to load from cache
        if not force_refresh and os.path.exists(cache_file_path):
            file_mod_timestamp = os.path.getmtime(cache_file_path)
            file_mod_date = datetime.fromtimestamp(file_mod_timestamp).date()
            if (date.today() - file_mod_date).days < self.cache_expiry_days:
                try:
                    with open(cache_file_path, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass # Cache corrupted, will proceed to fetch fresh data
                except Exception:
                    pass # Other cache read error, will proceed to fetch fresh data
        
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
            return data
        except error.URLError as e:
            raise Exception(f"Network Error fetching {cache_key} from {url}: {e.reason}")
        except error.HTTPError as e:
            raise Exception(f"API Error fetching {cache_key} from {url}: Status {e.code}, Reason {e.reason}")
        except json.JSONDecodeError as e:
            raise Exception(f"Data Parsing Error fetching {cache_key} from {url}: Failed to decode JSON. Error: {e}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during {cache_key} fetch from {url}: {e}")

def format_json_output(status: str, data: dict = None, message: str = None):
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
