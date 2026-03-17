#!/usr/bin/env python3
import subprocess
import json
import sys
import os
from pathlib import Path

# Setup path for imports
script_dir = Path(__file__).parent.parent
sys.path.append(str(script_dir / 'scripts'))

def load_stats_mapping():
    try:
        res = subprocess.run(["python3", "scripts/stats_mapper.py"], capture_output=True, text=True, cwd=str(script_dir))
        output = res.stdout
        if "--- Current League Stat Mapping ---" in output:
             json_str = output.split("--- Current League Stat Mapping ---")[1].strip()
             return json.loads(json_str)
    except:
         pass
    return {
      "9004003": "FGM/A", "5": "FG%", "9007006": "FTM/A", "8": "FT%",
      "10": "3PTM", "12": "PTS", "15": "REB", "16": "AST",
      "17": "ST", "18": "BLK", "19": "TO"
    }

def fetch_matchups():
    res = subprocess.run(["python3", "scripts/fetch_yahoo_raw_data.py", "matchups"], capture_output=True, text=True, cwd=str(script_dir))
    if res.returncode != 0:
         print(f"Error fetching matchups: {res.stderr}")
         sys.exit(1)
    try:
         return json.loads(res.stdout)
    except Exception as e:
         print(f"Failed to parse JSON: {e}")
         sys.exit(1)

def extract_team_stats(team_node, mapping):
    stats_list = team_node[1]['team_stats']['stats']
    parsed = {}
    for s in stats_list:
         stat = s['stat']
         stat_id = str(stat['stat_id'])
         val = stat['value']
         label = mapping.get(stat_id, stat_id)
         parsed[label] = val
    return parsed

def main():
    mapping = load_stats_mapping()
    raw = fetch_matchups()
    
    league = raw['fantasy_content']['league']
    scoreboard = league[1]['scoreboard']
    matchups = scoreboard['0']['matchups']
    
    target_matchup = None
    for k, m_node in matchups.items():
         if k == 'count': continue
         matchup = m_node['matchup']
         teams = matchup['0']['teams'] if '0' in matchup and 'teams' in matchup['0'] else matchup.get('teams')
         
         if not teams: continue
         
         has_team_6 = False
         for tk, t_node in teams.items():
              if tk == 'count': continue
              t_info = t_node['team'][0]
              for item in t_info:
                   if isinstance(item, dict) and 'team_id' in item:
                        if item['team_id'] in ['6', 6]:
                             has_team_6 = True
         if has_team_6:
              target_matchup = teams
              break

    if not target_matchup:
         print(json.dumps({"error": "Could not find Matchup for Team 6"}, indent=2))
         sys.exit(1)
         
    teams_stats = {}
    for tk, t_node in target_matchup.items():
         if tk == 'count': continue
         t_info = t_node['team'][0]
         team_id = None
         for item in t_info:
              if isinstance(item, dict) and 'team_id' in item:
                   team_id = str(item['team_id'])
         
         stats = extract_team_stats(t_node['team'], mapping)
         teams_stats[team_id] = stats

    print(json.dumps(teams_stats, indent=2))

if __name__ == "__main__":
    main()
