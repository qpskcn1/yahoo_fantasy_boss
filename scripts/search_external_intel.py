#!/usr/bin/env python3
import sys
import json
import requests

def search_reddit_intel(player_name):
    """
    Fetches news/discussions from Reddit r/fantasybball for a specific player.
    """
    # Reddit API requires a distinct User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (FantasyAgent/1.0)'
    }
    # Search within /r/fantasybball for the player name, sorted by hot/relevance
    # restrict_sr=on restricts to the subreddit
    url = f"https://www.reddit.com/r/fantasybball/search.json"
    params = {
        'q': player_name,
        'restrict_sr': 'on',
        'sort': 'relevance',  # or 'new' for latest
        't': 'week'  # timeframe: hour, day, week, month, year, all
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            extracted = []
            for post in posts:
                p = post.get('data', {})
                extracted.append({
                    "title": p.get('title'),
                    "score": p.get('score'),
                    "text": p.get('selftext')[:500] if p.get('selftext') else "", # trim text
                    "url": f"https://reddit.com{p.get('url')}"
                })
            return extracted
        else:
             return {"error": f"Reddit API failed with status: {response.status_code}"}
    except Exception as e:
         return {"error": f"Exception during Reddit search: {str(e)}"}

def search_external_intel(player_name):
    """Main function to gather internal."""
    intel_data = {
        "player_name": player_name,
        "reddit": search_reddit_intel(player_name),
        "rotowire_note": "Ensure to check official RotoWire player profile or RSS for live injury feeds."
    }
    print(json.dumps(intel_data, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: search_external_intel.py <player_name>"}, indent=2))
        sys.exit(1)

    player_name_arg = " ".join(sys.argv[1:])
    search_external_intel(player_name_arg)
