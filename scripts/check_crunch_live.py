
import sys
import os
import json
import requests
from pathlib import Path
from datetime import datetime

"""
Utility to check which players in a given team's roster have games on a specific date.
Uses ESPN's public scoreboard API to identify active NBA teams.
"""

def check_active_games(team_id, check_date=None):
    # Set up base directories
    base_dir = Path(__file__).resolve().parent.parent
    roster_path = base_dir / f'data/roster_team_{team_id}.json'
    
    if not check_date:
        # Default to today if no date provided
        check_date = datetime.today().strftime('%Y%02d%02d') # YYYYMMDD for ESPN
    else:
        # Remove hyphens for ESPN API compatibility
        check_date = str(check_date).replace('-', '')

    # Fetch NBA scoreboard from ESPN to see which teams are playing
    espn_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={check_date}"
    try:
        response = requests.get(espn_url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: Failed to fetch ESPN schedule for {check_date}: {e}")
        return

    games_data = response.json().get('events', [])
    teams_playing = set()
    for game in games_data:
        for competitor in game.get('competitions', [{}])[0].get('competitors', []):
            team_abbr = competitor.get('team', {}).get('abbreviation')
            if team_abbr:
                teams_playing.add(team_abbr.upper())

    # Map Yahoo team aliases to ESPN team abbreviations
    TEAM_ALIASES = {
        'GS': 'GSW', 'GSW': 'GS',
        'NO': 'NOP', 'NOP': 'NO',
        'NY': 'NYK', 'NYK': 'NY',
        'SA': 'SAS', 'SAS': 'SA',
        'WAS': 'WSH', 'WSH': 'WAS',
        'PHX': 'PHO', 'PHO': 'PHX'
    }

    # Load local roster data
    if not roster_path.exists():
        print(f"Error: Roster file not found: {roster_path}")
        return

    with open(roster_path, 'r') as f:
        roster_json = json.load(f)

    # Simple validation of Yahoo roster structure
    try:
        team_data = roster_json['fantasy_content']['team'][1]
        players_dict = team_data['roster']['0']['players']
    except (KeyError, IndexError):
        print("Error: Invalid roster JSON structure.")
        return

    playing_count = 0
    print(f"\n--- Roster Status for {check_date} ---")
    
    player_count_val = players_dict.get('count', 0)
    for i in range(player_count_val):
        player_info_list = players_dict[str(i)]['player']
        player_name = ""
        player_team = ""
        
        # Metadata extraction
        for info_item in player_info_list[0]:
            if isinstance(info_item, dict):
                if 'name' in info_item:
                    player_name = info_item['name']['full']
                if 'editorial_team_abbr' in info_item:
                    player_team = info_item['editorial_team_abbr'].upper()

        player_pos = player_info_list[1].get('selected_position', [{}, {}])[1].get('position', 'BN')
        
        # Check against active teams and aliases
        is_playing = (player_team in teams_playing or 
                     (player_team in TEAM_ALIASES and TEAM_ALIASES[player_team] in teams_playing))

        if is_playing and player_pos != 'BN':
            playing_count += 1
            
        print(f"{player_name:<25} ({player_team:>3}): {player_pos:<4} | Game: {'YES' if is_playing else 'NO'}")

    print(f"\nTotal active players (non-bench) playing on {check_date}: {playing_count}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check roster game status using ESPN API")
    parser.add_argument("--team-id", type=str, default="6", help="Yahoo Team ID")
    parser.add_argument("--date", type=str, help="Date to check (YYYY-MM-DD)")
    args = parser.parse_args()
    
    check_active_games(args.team_id, args.date)
