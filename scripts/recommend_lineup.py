
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

"""
Analyzes a fantasy basketball team's roster and suggests lineup optimizations 
based on active games and player performance metrics.
"""

def generate_recommendations(team_id, stats_date=None):
    # Determine base directory relative to the script location
    base_dir = Path(__file__).resolve().parent.parent
    roster_file = base_dir / f'data/roster_team_{team_id}.json'
    stats_file = base_dir / f'data/rich_stats_team_{team_id}.json'

    if not roster_file.exists() or not stats_file.exists():
        print(f"Error: Missing data files for team {team_id} at {base_dir}")
        return

    # Load statistics and roster data
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    with open(roster_file, 'r') as f:
        roster = json.load(f)

    # If no date provided, use today's date in YYYY-MM-DD format
    if not stats_date:
        stats_date = datetime.today().strftime('%Y-%m-%d')

    # List of teams with games on the analysis date
    # In a real scenario, this should be fetched from a schedule API
    # Defaulting to most commonly used NBA abbreviations
    teams_playing = {
        'UTAH', 'WSH', 'DAL', 'CHI', 'ATL', 'MIN', 'CLE', 'OKC', 'HOU', 'MIL', 
        'BKN', 'SA', 'SAS', 'MEM', 'MIA', 'DEN', 'PHI', 'LAC', 'LAL', 'BOS', 
        'TOR', 'IND', 'DET', 'GSW', 'GS', 'POR', 'NOP', 'NO', 'NYK', 'NY', 
        'PHX', 'PHO', 'CHA', 'ORL', 'SAC'
    }

    players_info = []

    # Handle various Yahoo JSON response structures
    try:
        root = roster.get('fantasy_content', {})
        if 'team' in root:
            team_data = root['team'][1]
        elif 'league' in root:
            team_data = root['league'][1]['teams'][0]['team'][1]
        else:
            print("Error: Unrecognized roster JSON structure.")
            return
    except Exception as e:
        print(f"Error parsing roster for team {team_id}: {e}")
        return

    # Extract player details and calculate custom performance score
    players_list = team_data.get('roster', {}).get('0', {}).get('players', {})
    count = players_list.get('count', 0)
    
    for i in range(count):
        players_in_list = players_list.get(str(i), {}).get('player', [])
        p_name = ""
        p_team = ""
        p_key = ""
        p_status = ""
        
        # Player attributes are stored in a list of dicts/lists
        for info in players_in_list[0]:
            if isinstance(info, dict):
                if 'name' in info: p_name = info['name']['full']
                if 'editorial_team_abbr' in info: p_team = info['editorial_team_abbr'].upper()
                if 'player_key' in info: p_key = info['player_key']
                if 'status' in info: p_status = info['status']
        
        # Determine current assigned position
        p_pos = "BN"
        if len(players_in_list) > 1 and 'selected_position' in players_in_list[1]:
            p_pos = players_in_list[1]['selected_position'][1].get('position', 'BN')
        
        # Check if the player's team has a game today
        is_playing = p_team in teams_playing
        
        player_stats = stats.get(p_key, {})
        season_stats = player_stats.get('stats_season', {})
        
        def get_val(key, default='0'):
            try:
                val = season_stats.get(key, default)
                return float(str(val).replace(',', ''))
            except:
                return 0.0
        
        # Weighted score (Fantasy Points style) to evaluate relative contribution
        score = (get_val('PTS') + get_val('REB')*1.2 + get_val('AST')*1.5 + 
                 get_val('ST')*2.5 + get_val('BLK')*2.5 - get_val('TO')*1.5)
        
        players_info.append({
            'name': p_name,
            'pos': p_pos,
            'is_playing': is_playing,
            'score': score,
            'injury': player_stats.get('injury') or p_status
        })

    print(f"\n--- Team {team_id} Lineup Analysis ({stats_date}) ---")
    active_no_game = []
    bench_with_game = []
    active_with_game = []

    # Categorize players based on current roster slot and game status
    for p in players_info:
        if p['pos'] in ['IL', 'IL+']: 
            continue
        
        if p['pos'] == 'BN':
            if p['is_playing']:
                bench_with_game.append(p)
        else:
            if p['is_playing']:
                active_with_game.append(p)
            else:
                active_no_game.append(p)

    # Sort categories to find best and worst performers
    active_no_game.sort(key=lambda x: x['score'], reverse=True)
    bench_with_game.sort(key=lambda x: x['score'], reverse=True)
    active_with_game.sort(key=lambda x: x['score']) # Lowest scores first

    # Print summary status
    for p in sorted(players_info, key=lambda x: x['score'], reverse=True):
        if p['pos'] in ['IL', 'IL+']: continue
        status = "PLAYING" if p['is_playing'] else "NO GAME"
        idx = f"({p['pos']})"
        print(f"{status:<8}: {p['name']:<25} {idx:<6} Score: {p['score']:>5.1f}")

    print("\n[ RECOMMENDATIONS ]")
    # Priority 1: Replace active players who have no game with anyone from the bench who has a game
    while active_no_game and bench_with_game:
        idle = active_no_game.pop(0)
        hot = bench_with_game.pop(0)
        print(f"CRITICAL: Activate {hot['name']} (BN) to replace {idle['name']} {idle['pos']}.")
        active_with_game.append(hot)
        active_with_game.sort(key=lambda x: x['score'])

    # Priority 2: Suggest upgrades if a bench player is significantly better than a currently active player
    for hot in bench_with_game:
        for cold in active_with_game:
            if hot['score'] > cold['score'] + 8.0: # 8 point threshold for "Strategic Swap"
                print(f"STRATEGIC: Swap {cold['name']} ({cold['pos']}) for higher ceiling {hot['name']} (BN).")
                active_with_game.remove(cold)
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yahoo Fantasy Lineup Optimizer")
    parser.add_argument("--team-id", type=str, default="6", help="The Yahoo Team ID to analyze")
    parser.add_argument("--date", type=str, help="Date for analysis (YYYY-MM-DD)")
    args = parser.parse_args()
    generate_recommendations(args.team_id, args.date)
