#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
from pathlib import Path


# Load Environment Variables
# Try loading from the config/ directory relative to this script
def load_env_manual(path):
    import os
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

script_dir = Path(__file__).parent.parent
dotenv_path = script_dir / 'config' / '.env'
load_env_manual(dotenv_path)
  # fallback to current working dir

TOKEN_FILE = script_dir / 'config' / '.tokens.json'

#!/usr/bin/env python3
import os
import sys
import json
import requests
from yahoo_oauth import get_valid_access_token

def fetch_yahoo_raw_data(endpoint_type, params=None):
    """
    Fetches raw data from Yahoo Fantasy API.
    Endpoint Type supports: league, team, roster, matchups.
    """
    access_token = get_valid_access_token()
    league_key = os.getenv('YAHOO_LEAGUE_KEY')
    team_id = os.getenv('YAHOO_TEAM_ID')

    base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    url_map = {
        "league": f"{base_url}/league/{league_key}/standings",
        "settings": f"{base_url}/league/{league_key}/settings",
        "team": f"{base_url}/team/{league_key}.t.{team_id}/stats",
        "roster": f"{base_url}/team/{league_key}.t.{team_id}/roster",
        "matchups": f"{base_url}/league/{league_key}/scoreboard",
        "discover": f"{base_url}/users;use_login=1/games;game_keys=nba/teams"
    }

    if endpoint_type not in url_map:
         print(json.dumps({"error": f"Unsupported endpoint type: {endpoint_type}. Valid options: league, team, roster, matchups, discover"}, indent=2))
         sys.exit(1)

    if endpoint_type != "discover" and not league_key:
        print(json.dumps({"error": f"YAHOO_LEAGUE_KEY is required for endpoint '{endpoint_type}'."}, indent=2))
        sys.exit(1)


    url = url_map[endpoint_type]
    query_params = {"format": "json"}
    if params:
         query_params.update(params)

    try:
        response = requests.get(url, headers=headers, params=query_params)
        if response.status_code == 200:
             print(json.dumps(response.json(), indent=2))
        else:
             print(json.dumps({
                 "error": f"API call failed with status: {response.status_code}",
                 "detail": response.text
             }, indent=2))
             sys.exit(1)
    except Exception as e:
         print(json.dumps({"error": f"Exception during API call: {str(e)}"}, indent=2))
         sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: fetch_yahoo_raw_data.py <endpoint_type> [json_params]"}, indent=2))
        sys.exit(1)

    endpoint = sys.argv[1].lower()
    params = {}
    if len(sys.argv) > 2:
         try:
             params = json.loads(sys.argv[2])
         except json.JSONDecodeError:
             print(json.dumps({"error": "Params must be a valid JSON string."}, indent=2))
             sys.exit(1)

    fetch_yahoo_raw_data(endpoint, params)


