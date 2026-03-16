#!/usr/bin/env python3
import os
import sys
import json
import requests
from yahoo_oauth import get_valid_access_token

def get_waiver_pool_stats():
    """
    Fetches top waiver wire / free agent players from Yahoo Fantasy League.
    """
    access_token = get_valid_access_token()
    league_key = os.getenv('YAHOO_LEAGUE_KEY')

    if not league_key:
        print(json.dumps({"error": "YAHOO_LEAGUE_KEY is required in environment."}, indent=2))
        sys.exit(1)

    url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    # status=W (Waivers), status=FA (Free Agents), status=W_FA (Waivers or Free Agents)
    # sort=AR (Actual Rank), sort=OR (Overall Rank)
    # sort_type=season, sort_type=last_7_days, sort_type=last_14_days
    params = {
        "format": "json",
        "status": "A",  # Available players
        "sort": "AR",      # Sorted by actual rank
        "count": 15         # Top 15 players
    }

    try:
        response = requests.get(url, headers=headers, params=params)
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
    get_waiver_pool_stats()
