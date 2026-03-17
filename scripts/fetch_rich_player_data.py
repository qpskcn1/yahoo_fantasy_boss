#!/usr/bin/env python3
import os
import sys
import json
import requests
import datetime
import argparse
from pathlib import Path

# Setup path for imports
script_dir = Path(__file__).parent.parent
sys.path.append(str(script_dir / 'scripts'))

from yahoo_oauth import get_valid_access_token
from stats_mapper import get_stats_mapping

def load_env_manual(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

def get_league_meta(access_token, league_key):
    """Fetches full league metadata to determine current week and current_date."""
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}"
    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json" }
    response = requests.get(url, headers=headers, params={"format": "json"})
    
    if response.status_code == 200:
         try:
              parsed = response.json()
              league_node = parsed['fantasy_content']['league'][0]
              current_week = league_node.get('current_week', 21)
              current_date = league_node.get('current_date', "2026-03-17")
              return current_week, current_date
         except Exception:
              pass
    return 21, "2026-03-17"

def fetch_top_players(access_token, league_key, sort_by="AR", count=25):
    """Fetches top players by status A from league/players endpoint."""
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;out=percent_owned"
    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json" }
    params = {
        "format": "json",
        "status": "A",
        "sort": sort_by,
        "count": count
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
         print(f"-> Error fetching sort={sort_by}: {response.status_code}")
         return {}
    try:
         return response.json()['fantasy_content']['league'][1]['players']
    except Exception:
         return {}

def fetch_team_roster_players(access_token, league_key, team_id):
    """Fetches player keys from a specific team roster."""
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/team/{league_key}.t.{team_id}/roster"
    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json" }
    response = requests.get(url, headers=headers, params={"format": "json"})
    
    if response.status_code != 200:
         print(f"-> Error fetching roster for team {team_id}: {response.status_code}")
         return []
    
    try:
         parsed = response.json()
         team_node = parsed['fantasy_content']['team']
         players = team_node[1]['roster']['0']['players']
         player_keys = []
         for k, v in players.items():
              if k == 'count': continue
              p_key = v['player'][0][0]['player_key']
              player_keys.append(p_key)
         return player_keys
    except Exception as e:
         print(f"-> Error parsing roster: {e}")
         return []

def fetch_and_parse_metadata_batch(access_token, league_key, player_keys):
    """Enriches player keys with percent_owned and notes_recency using generic lookup."""
    if not player_keys:
         return {}
         
    keys_str = ",".join(player_keys)
    url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;player_keys={keys_str};out=percent_owned"
    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json" }
    response = requests.get(url, headers=headers, params={"format": "json"})
    
    if response.status_code != 200:
         print(f"-> Error fetching metadata batch: {response.status_code}")
         return {}
         
    try:
         parsed = response.json()
         return parsed['fantasy_content']['league'][1]['players']
    except Exception as e:
         print(f"-> Error parsing metadata batch: {e}")
         return {}

def parse_players_list(players_list, compiled_data, player_keys_list):
    """Parses player dictionary list nodes into compiled_data schema."""
    if not players_list:
         return

    for k, v in players_list.items():
        if k == 'count': continue
        try:
             p_obj = v['player']
             meta = p_obj[0]
             
             player_key = None
             name_full = ""
             display_pos = ""
             injury_status = None

             for item in meta:
                  if 'player_key' in item: player_key = item['player_key']
                  if 'name' in item: name_full = item['name']['full']
                  if 'display_position' in item: display_pos = item['display_position']
                  if 'status' in item: injury_status = item['status']

             if not player_key: continue
             
             notes_recency = "No notes"
             for item in meta:
                  if isinstance(item, dict) and 'player_notes_last_timestamp' in item:
                       ts = int(item['player_notes_last_timestamp'])
                       now_ts = int(datetime.datetime.now().timestamp())
                       diff = now_ts - ts
                       if diff < 3600: notes_recency = f"{diff // 60} min ago"
                       elif diff < 86400: notes_recency = f"{diff // 3600} hours ago"
                       else: notes_recency = f"{diff // 86400} days ago"

             pct_owned = {}
             for i in p_obj:
                  if isinstance(i, dict) and 'percent_owned' in i:
                       for sub_item in i['percent_owned']:
                            if 'value' in sub_item: pct_owned['value'] = sub_item['value']
                            if 'delta' in sub_item: pct_owned['delta'] = sub_item['delta']

             if player_key not in compiled_data:
                  player_keys_list.append(player_key)
                  compiled_data[player_key] = {
                      "player_key": player_key,
                      "name": name_full,
                      "position": display_pos,
                      "injury": injury_status,
                      "percent_owned": pct_owned,
                      "notes_recency": notes_recency,
                      "stats_season": {},
                      "stats_recent_days": {}
                  }
        except Exception as e:
             pass

def fetch_batch_stats(access_token, league_key, player_keys, stats_type="season", extras="", game_level=False):
    """Fetches batch stats for a list of player keys (league or game level)."""
    if not player_keys: return {}
    keys_str = ",".join(player_keys)
    game_key = league_key.split('.')[0] if '.' in league_key else "466"

    if game_level:
         url = f"https://fantasysports.yahooapis.com/fantasy/v2/game/{game_key}/players;player_keys={keys_str}/stats;type={stats_type}{extras}"
    else:
         url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;player_keys={keys_str}/stats;type={stats_type}{extras}"

    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json" }
    response = requests.get(url, headers=headers, params={"format": "json"})
    if response.status_code != 200:
         return {}
    try:
         node = response.json()['fantasy_content']
         return node['league'][1]['players'] if 'league' in node else node['game'][1]['players']
    except Exception:
         return {}

def main():
    parser = argparse.ArgumentParser(description="Fetch rich player data (Waivers or Teams)")
    parser.add_argument("--mode", type=str, choices=['waiver', 'team'], default='waiver')
    parser.add_argument("--team-id", type=str, help="Specific Yahoo Team ID required for mode=team")
    args = parser.parse_args()

    dotenv_path = script_dir / 'config' / '.env'
    load_env_manual(dotenv_path)

    league_key = os.getenv('YAHOO_LEAGUE_KEY')
    access_token = get_valid_access_token()
    mapping = get_stats_mapping()

    compiled_data = {}
    player_keys = []

    if args.mode == 'waiver':
         print("-> Fetching Waiver candidates by Actual Rank & Overall Rank...")
         ar_players = fetch_top_players(access_token, league_key, sort_by="AR", count=30)
         or_players = fetch_top_players(access_token, league_key, sort_by="OR", count=30)
         parse_players_list(ar_players, compiled_data, player_keys)
         parse_players_list(or_players, compiled_data, player_keys)

    elif args.mode == 'team':
         tid = args.team_id or os.getenv('YAHOO_TEAM_ID', '6')
         print(f"-> Fetching Roster for Team ID: {tid}...")
         team_keys = fetch_team_roster_players(access_token, league_key, tid)
         if not team_keys:
              print("-> No players found on roster.")
              sys.exit(1)
         
         # Enrich metadata 
         print(f"-> Enriching metadata for {len(team_keys)} players...")
         meta_batch = fetch_and_parse_metadata_batch(access_token, league_key, team_keys)
         parse_players_list(meta_batch, compiled_data, player_keys)

    unique_count = len(compiled_data)
    print(f"-> Combined unique candidate count: {unique_count}")

    if unique_count == 0:
         print("No players found.")
         sys.exit(0)

    # Last 5 days absolute layout
    current_week, current_date_str = get_league_meta(access_token, league_key)
    try: base_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d")
    except: base_date = datetime.datetime.now()
         
    past_dates = [(base_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 6)]
    past_dates.reverse()

    batches = [player_keys[i:i + 25] for i in range(0, unique_count, 25)]
    
    for idx, batch_keys in enumerate(batches):
         season_stats = fetch_batch_stats(access_token, league_key, batch_keys, stats_type="season")
         if season_stats:
              for k, v in season_stats.items():
                   if k == 'count': continue
                   try:
                        p_obj = v['player']
                        p_key = p_obj[0][0]['player_key']
                        if p_key in compiled_data:
                             stats_node = p_obj[1]
                             if 'player_stats' in stats_node:
                                  for s in stats_node['player_stats']['stats']:
                                       sid = str(s['stat']['stat_id'])
                                       if sid in mapping:
                                            compiled_data[p_key]["stats_season"][mapping[sid]] = s['stat']['value']
                   except: pass

         for d_str in past_dates:
              day_stats = fetch_batch_stats(access_token, league_key, batch_keys, stats_type="date", extras=f";date={d_str}")
              if day_stats:
                   for k, v in day_stats.items():
                        if k == 'count': continue
                        try:
                             p_obj = v['player']
                             p_key = p_obj[0][0]['player_key']
                             if p_key in compiled_data:
                                  stats_node = p_obj[1]
                                  if 'player_stats' in stats_node:
                                       if d_str not in compiled_data[p_key]["stats_recent_days"]:
                                            compiled_data[p_key]["stats_recent_days"][d_str] = {}
                                       for s in stats_node['player_stats']['stats']:
                                            sid = str(s['stat']['stat_id'])
                                            if sid in mapping:
                                                 compiled_data[p_key]["stats_recent_days"][d_str][mapping[sid]] = s['stat']['value']
                        except: pass

    final_output = {
         "_metadata": {
              "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "league_key": league_key,
              "current_date": current_date_str,
              "mode": args.mode
         }
    }
    final_output.update(compiled_data)

    fname = f"rich_stats_{args.mode}.json" if args.mode != 'team' else f"rich_stats_team_{args.team_id or os.getenv('YAHOO_TEAM_ID','6')}.json"
    output_path = script_dir / 'data' / fname
    
    with open(output_path, 'w') as f:
         json.dump(final_output, f, indent=2)

    print(f"-> Saved aggregator output to: {output_path} (Players: {unique_count})")

if __name__ == "__main__":
    main()
