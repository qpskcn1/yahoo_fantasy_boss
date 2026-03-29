
import json
import argparse
from pathlib import Path

"""
Aggregates and compares season-long statistics between two fantasy basketball teams.
Used to identify high-level strengths and weaknesses in a matchup.
"""

def aggregate_team_stats(team_id, data_dir):
    stats_file = data_dir / f"rich_stats_team_{team_id}.json"
    if not stats_file.exists():
        print(f"Error: Missing stats file for team {team_id}")
        return None
        
    with open(stats_file, 'r') as f:
        data = json.load(f)
        
    categories = ['3PTM', 'PTS', 'REB', 'AST', 'ST', 'BLK', 'TO']
    totals = {c: 0.0 for c in categories}
    fgm, fga, ftm, fta = 0.0, 0.0, 0.0, 0.0
    
    for k, v in data.items():
        if k == '_metadata': continue
        stats = v.get('stats_season', {})
        
        # Accumulate counting stats
        for cat in categories:
            try:
                val = str(stats.get(cat, '0')).replace(',', '')
                totals[cat] += float(val)
            except: pass
            
        # Accumulate percentages (logic handled by summing made/attempted)
        def parse_frac(s):
            try:
                m, a = map(float, str(s).split('/'))
                return m, a
            except: 
                return 0.0, 0.0

        if 'FGM/A' in stats:
            m, a = parse_frac(stats['FGM/A'])
            fgm += m; fga += a
        elif 'FG' in stats:
            m, a = parse_frac(stats['FG'])
            fgm += m; fga += a
            
        if 'FTM/A' in stats:
            m, a = parse_frac(stats['FTM/A'])
            ftm += m; fta += a
        elif 'FT' in stats:
            m, a = parse_frac(stats['FT'])
            ftm += m; fta += a
            
    fg_pct = (fgm / fga) if fga > 0 else 0
    ft_pct = (ftm / fta) if fta > 0 else 0
    
    return {
        'FG%': fg_pct,
        'FT%': ft_pct,
        '3PTM': totals['3PTM'],
        'PTS': totals['PTS'],
        'REB': totals['REB'],
        'AST': totals['AST'],
        'ST': totals['ST'],
        'BLK': totals['BLK'],
        'TO': totals['TO']
    }

def main():
    parser = argparse.ArgumentParser(description="Compare season stats for two teams")
    parser.add_argument("--t1", type=str, default="6", help="Team 1 ID (Your Team)")
    parser.add_argument("--t2", type=str, default="5", help="Team 2 ID (Opponent)")
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    t1_data = aggregate_team_stats(args.t1, data_dir)
    t2_data = aggregate_team_stats(args.t2, data_dir)
    
    if not t1_data or not t2_data:
        return

    # Print header
    header = f"{'Category':<10} | {'Team ' + args.t1:<15} | {'Team ' + args.t2:<15} | {'Diff':<15}"
    print(f"\n{header}")
    print("-" * len(header))
    
    for c in t1_data.keys():
        v1 = t1_data[c]
        v2 = t2_data[c]
        diff = v1 - v2
        
        if c in ['FG%', 'FT%']:
            print(f"{c:<10} | {v1:.4f}          | {v2:.4f}          | {diff:+.4f}")
        else:
            # For TO, lower is better, so we invert the diff representation in logic if needed,
            # but usually just raw diff is fine for season totals.
            print(f"{c:<10} | {int(v1):<15} | {int(v2):<15} | {int(diff):+d}")

if __name__ == "__main__":
    main()
