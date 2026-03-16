#!/usr/bin/env python3
import os
import sys
import json
import requests
from pathlib import Path


def load_env_manual(path):
    import os
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()

script_dir = Path(__file__).parent.parent
dotenv_path = script_dir / 'config' / '.env'
load_env_manual(dotenv_path)


TOKEN_FILE = script_dir / 'config' / '.tokens.json'

def setup_oauth():
    """
    Guides the user through the first-time Yahoo OAuth2 authorization flow.
    """
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("Error: YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET must be set in config/.env")
        print("Please create `config/.env` based on `config/.env.example` first.")
        sys.exit(1)

    # 1. Generate Auth URL
    # Using 'oob' (Out Of Band) or 'oob' setup for desktop/cli apps
    redirect_uri = 'oob' 
    auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&language=en-us"

    print("\n--- Yahoo Fantasy OAuth2 Setup ---")
    print("1. Visit the following URL in your browser to authorize access:")
    print(f"\n{auth_url}\n")
    print("2. Log in to Yahoo and click 'Allow'.")
    print("3. You will be provided with an Authorization Code (or verification code).")
    
    auth_code = input("\nEnter the Authorization Code here: ").strip()

    if not auth_code:
        print("Authorization code cannot be empty.")
        sys.exit(1)

    # 4. Exchange code for tokens
    print("\nExchanging code for tokens...")
    url = "https://api.login.yahoo.com/oauth2/get_token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'code': auth_code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
             tokens = response.json()
             # Add expires_at timestamp
             import time
             tokens['expires_at'] = int(time.time()) + tokens.get('expires_in', 3600)
             
             TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
             with open(TOKEN_FILE, 'w') as f:
                 json.dump(tokens, f, indent=2)
             
             print("\n✅ Setup Successful! Tokens saved to config/.tokens.json")
             print("You can now test it with:")
             print("  python3 scripts/fetch_yahoo_raw_data.py league")
        else:
             print(f"\n❌ Exchange failed with status {response.status_code}:")
             print(response.text)
    except Exception as e:
         print(f"\n❌ Exception during exchange: {str(e)}")

if __name__ == "__main__":
    setup_oauth()
