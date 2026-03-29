
import json
import os
import argparse
from pathlib import Path

"""
Analyzes waiver wire players to identify defensive specialists (Steals and Blocks).
Calculates a 'defensive score' based on recent performance averages and games 
remaining in the week to find high-impact streaming targets.
"""

def analyze_waiver_defensive_potential(waiver_file):
    # Set up base directories
    base_dir = Path(__file__).resolve().parent.parent
    waiver_path = base_dir / waiver_file
    
    if not waiver_path.exists():
        print(f"Error: Waiver data file not found: {waiver_path}")
        return []

    with open(waiver_path, 'r') as f:
        data = json.load(f)
    
    players = []
    for player_id, player_data in data.items():
        if player_id == '_metadata': 
            continue
            
        # Skip injured players if information is available
        if player_data.get('injury'): 
            continue
        
        name = player_data.get('name')
        team = player_data.get('team')
        rem_games = player_data.get('remaining_games', 0)
        
        # Calculate recent averages (e.g., last 7-14 days included in data)
        recent_stats = player_data.get('stats_recent_days', {})
        active_days = 0
        total_st = 0
        total_blk = 0
        
        for date_str, game_stats in recent_stats.items():
            # Check if player actually played (FGM/A is a good proxy for activity)
            if game_stats.get('FGM/A') != '-/-' and game_stats.get('FGM/A') != '0/0':
                active_days += 1
                try:
                    total_st += int(game_stats.get('ST', 0))
                except (ValueError, TypeError): 
                    pass
                try:
                    total_blk += int(game_stats.get('BLK', 0))
                except (ValueError, TypeError): 
                    pass
        
        # Calculate defensive potential only for active players
        if active_days > 0:
            avg_st = total_st / active_days
            avg_blk = total_blk / active_days
            # Combined projected total remaining defensive contribution
            score = (avg_st + avg_blk) * rem_games
            
            players.append({
                'name': name,
                'team': team,
                'remaining_games': rem_games,
                'avg_st': round(avg_st, 2),
                'avg_blk': round(avg_blk, 2),
                'projected_def_total': round(score, 2)
            })
            
    # Return top 15 most promising defensive streamers
    players.sort(key=lambda x: x['projected_def_total'], reverse=True)
    return players[:15]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze waiver wire for defensive stats")
    parser.add_argument("--file", type=str, default="data/rich_stats_waiver.json", help="Waiver data JSON path")
    args = parser.parse_args()
    
    # Run analysis and output results in JSON for further processing
    results = analyze_waiver_defensive_potential(args.file)
    print(json.dumps(results, indent=2))
