import os
import sys
import json
import time
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

def get_tokens_from_file():
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_tokens_to_file(tokens):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token():
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    tokens = get_tokens_from_file()
    refresh_token = tokens.get('refresh_token') or os.getenv('YAHOO_REFRESH_TOKEN')

    if not client_id or not client_secret or not refresh_token:
        print(json.dumps({"error": "Missing YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, or YAHOO_REFRESH_TOKEN (in .env or .tokens.json)"}, indent=2))
        sys.exit(1)

    url = 'https://api.login.yahoo.com/oauth2/get_token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'oob',
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            new_tokens = response.json()
            if 'refresh_token' not in new_tokens:
                new_tokens['refresh_token'] = refresh_token
            new_tokens['expires_at'] = int(time.time()) + new_tokens.get('expires_in', 3600)
            save_tokens_to_file(new_tokens)
            return new_tokens.get('access_token')
        else:
            print(json.dumps({"error": f"Failed to refresh token: {response.status_code}", "detail": response.text}, indent=2))
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Exception during token refresh: {str(e)}"}, indent=2))
        sys.exit(1)

def get_valid_access_token():
    tokens = get_tokens_from_file()
    expires_at = tokens.get('expires_at', 0)
    now = int(time.time())

    if tokens.get('access_token') and (expires_at - now) > 300:
        return tokens.get('access_token')
    return refresh_access_token()
