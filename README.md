# 🏀 Yahoo Fantasy Boss - Agent Skill

A portable, shareable Agent Skill designed for professional Fantasy Basketball managers. It separates data fetching (Python) from analysis (AI reasoning), enabling Claude to provide 9-Cat comparisons and strategy advice.

## 📂 Structure
- `SKILL.md`: Core system prompt with instructions for AI reasoning.
- `scripts/`: Python execution files loaded on demand.
- `config/`: Configuration credentials storage.

---

## 🛠️ Step-by-Step Setup

### Phase 1: Obtain Yahoo Developer Access
1. Visit [Yahoo Developer Network](https://developer.yahoo.com/apps/).
2. Click **Create an App**.
3. Fill details:
   - **Application Name**: Yahoo Fantasy Boss
   - **Application Type**: **Installed Application** (required for desktop/CLI).
   - **API Permissions**: Check **Fantasy Sports** (Read-only or Read/Write).
4. Click **Create App** and copy the **Client ID** and **Client Secret**.

---

### Phase 2: Configuration ⚙️
1. Locate the `yahoo_fantasy_boss/` directory.
2. Inside `config/`, copy `.env.example` to `.env`.
   ```bash
   cp config/.env.example config/.env
   ```
3. Open `config/.env` and replace placeholders with your credentials:
   - `YAHOO_CLIENT_ID` = `your_id`
   - `YAHOO_CLIENT_SECRET` = `your_secret`
   - `YAHOO_LEAGUE_KEY` = `your_league_id` (e.g., `422.l.12345`)
   - `YAHOO_TEAM_ID` = `your_team_id`

---

### Phase 3: First-time Authentication 🔐
If this is your first time setting it up, you need to generate a valid refresh token.
1. Run the interactive setup script:
   ```bash
   python3 scripts/setup_oauth.py
   ```
2. Follow the prompt to visit the URL, agree to permissions, and paste the Authorization Code back.
3. This creates `config/.tokens.json`. **Do not share this file.**

---
 
 ## 🚀 Operations (Data Aggregation)
 Before running analysis prompts, you must run the following python aggregators to pull downstream calculations:
 
 ```bash
 # 1. Fetch Waiver Candidates (Top 30 Actual/Overall Rank)
 python3 scripts/fetch_rich_player_data.py --mode waiver
 
 # 2. Fetch Team Roster Candidates
 python3 scripts/fetch_rich_player_data.py --mode team --team-id <TEAM_ID>
 ```
 *Outputs are saved to `data/rich_stats_<mode>.json` with full updates containing notes_recency items and 5-day delta statistics dashboards.*
 
 ---
 
 ## 🤖 Usage in Claude Desktop / Code

To combine with Claude, place this directory on your local disk. Add the following config rule or ensure Claude has access to this directory structure to run bash.

**Claude Desktop Configuration (`claude_desktop_config.json`)**:
```json
{
  "mcpServers": {
    "yahoo-boss-skill": {
      "command": "python3",
      "args": [
        "scripts/fetch_yahoo_raw_data.py",
        "league"
      ],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```
*Tip: Or simply use Claude Desktop with Bash tool enabled, and feed the `SKILL.md` instructions into your System Prompt to coordinate calls.*

---

## 🧠 AI Reasoning Principles (Inside SKILL.md)
When Claude reads `SKILL.md`, it is ordered to:
1. **Compare Categories (9-Cat)**: Differential gap analysis between you and the match-up opponent.
2. **Cross-Reference Reddit Intel**: Search player hype or injury rumors using `scripts/search_external_intel.py`.
3. **Synthesize Strategy**: Give Drop/Add recommendations leveraging Waiver stats and differentials.
