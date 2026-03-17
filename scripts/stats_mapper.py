#!/usr/bin/env python3
import os
import sys
import json
import requests
from pathlib import Path

# Setup path for imports
script_dir = Path(__file__).parent.parent
sys.path.append(str(script_dir / 'scripts'))

from yahoo_oauth import get_valid_access_token

def load_env_manual(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

def get_stats_mapping():
    """
    Returns the stat mapping dictionary for the current league.
    Auto-caches to config/stats_mapping_<league_id>.json if not found.
    """
    dotenv_path = script_dir / 'config' / '.env'
    load_env_manual(dotenv_path)

    league_key = os.getenv('YAHOO_LEAGUE_KEY')
    if not league_key:
        raise ValueError("YAHOO_LEAGUE_KEY is required in environment config.")

    cache_file = script_dir / 'data' / f"stats_mapping_{league_key}.json"

    # Step 1: Check cache
    if cache_file.exists():
        with open(cache_file, 'r') as f:
             # print(f"-> Loaded stats mapping from cache: {cache_file.name}")
             return json.load(f)

    # Step 2: Auto-Generate Core Cache
    print(f"-> Cache not found. Fetching league settings for: {league_key}...")
    access_token = get_valid_access_token()
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/settings"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    params = {"format": "json"}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
             raise Exception(f"API Failed: {response.status_code} {response.text}")

        parsed = response.json()
        league_data = parsed['fantasy_content']['league']
        
        stat_mapping = {}
        for item in league_data:
             if isinstance(item, dict) and 'settings' in item:
                  settings = item['settings'][0]
                  stats = settings['stat_categories']['stats']
                  for s in stats:
                       stat = s['stat']
                       stat_mapping[str(stat['stat_id'])] = stat['display_name']

        if not stat_mapping:
             raise ValueError("Could not parse stat categories from settings response.")

        # Save Cache
        with open(cache_file, 'w') as f:
             json.dump(stat_mapping, f, indent=2)
        print(f"-> Auto-generated and saved mapping: {cache_file.name}")

        return stat_mapping

    except Exception as e:
        print(f"-> Error generating stats mapping: {str(e)}")
        raise e

if __name__ == "__main__":
    try:
         mapping = get_stats_mapping()
         print("\n--- Current League Stat Mapping ---")
         print(json.dumps(mapping, indent=2))
    except Exception as e:
         print(f"Failed to execute: {e}")

