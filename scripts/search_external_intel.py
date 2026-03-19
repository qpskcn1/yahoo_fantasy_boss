#!/usr/bin/env python3
import sys
import json
import requests
import xml.etree.ElementTree as ET
import re
import html

# Common User-Agent to bypass basic bot detection
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_html(raw_html):
    """Removes HTML tags from a string."""
    if not raw_html:
        return ""
    cleanr = re.compile('<[^<]+?>')
    cleantext = re.sub(cleanr, '', html.unescape(raw_html))
    return cleantext.strip()

def fuzzy_match(player_name, text):
    """Checks if player name or last name is in text (case-insensitive)."""
    if not text:
        return False
    player_name = player_name.lower()
    text = text.lower()
    if player_name in text:
        return True
    
    # Try matching last name only if it's long enough
    parts = player_name.split()
    if len(parts) > 1:
        last_name = parts[-1]
        if len(last_name) > 3 and last_name in text:
            return True
            
    return False

def search_reddit_intel(player_name):
    """Fetches news/discussions from Reddit via RSS (Atom) search."""
    url = "https://www.reddit.com/r/fantasybball/search.rss"
    params = {
        'q': player_name,
        'restrict_sr': 'on',
        'sort': 'new',
        't': 'week'
    }
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, params=params, timeout=10)
        if response.status_code == 403:
             return {"error": "Reddit RSS access forbidden (403). Try manual search."}
        if response.status_code != 200:
             return {"error": f"Reddit RSS failed: {response.status_code}"}
        
        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', namespace)
        
        extracted = []
        for entry in entries:
            title = entry.find('atom:title', namespace).text
            content_node = entry.find('atom:content', namespace)
            content = clean_html(content_node.text) if content_node is not None else ""
            link_node = entry.find('atom:link', namespace)
            link = link_node.attrib.get('href') if link_node is not None else ""
            
            extracted.append({
                "title": title,
                "text": content[:500],
                "url": link
            })
        return extracted
    except Exception as e:
        return {"error": f"Reddit search exception: {str(e)}"}

def search_rotowire_intel(player_name):
    """Fetches news from the full RotoWire NBA news page (better than RSS)."""
    url = "https://www.rotowire.com/basketball/news.php"
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code != 200:
            return {"error": f"RotoWire page fetch failed: {response.status_code}"}
        
        # We'll use a regex to extract news items from the HTML.
        # RotoWire items are usually inside div class="news-update ..."
        # We split by "news-update" to catch all variations.
        # Split by the specific div class that starts a news item
        # Using \b to ensure we match 'news-update' but not 'news-update__headline'
        items = re.split(r'<div[^>]*class="[^"]*\bnews-update\b[^"]*"', response.text)
        
        extracted = []
        for item in items[1:]:
            if fuzzy_match(player_name, item):
                # Try to find headline
                title_match = re.search(r'class="news-update__headline"[^>]*>([^<]+)</a>', item)
                title = html.unescape(title_match.group(1).strip()) if title_match else "RotoWire Update"
                
                # Try to find news content
                desc_match = re.search(r'class="news-update__news"[^>]*>(.*?)</div>', item, re.DOTALL)
                desc = clean_html(desc_match.group(1)) if desc_match else clean_html(item[:500])
                
                extracted.append({
                    "title": f"RotoWire: {title}",
                    "text": desc[:500], # Keep the truncation here
                    "url": url # Use the function's URL variable
                })
        return extracted if extracted else "No recent RotoWire notes found."
    except Exception as e:
        return {"error": f"RotoWire search exception: {str(e)}"}

def search_rss_generic(player_name, url, source_name):
    """Generic RSS search for sources like CBS and ESPN."""
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        if response.status_code != 200:
            return []
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        extracted = []
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            if fuzzy_match(player_name, title) or fuzzy_match(player_name, desc):
                extracted.append({
                    "source": source_name,
                    "title": title,
                    "text": clean_html(desc)[:500],
                    "url": link
                })
        return extracted
    except Exception:
        return []

def search_external_intel(player_name):
    """Aggregates intelligence from multiple sources."""
    intel_data = {
        "player_name": player_name,
        "reddit": search_reddit_intel(player_name),
        "rotowire": search_rotowire_intel(player_name),
        "cbs_espn": []
    }
    
    # Generic RSS sources
    sources = [
        ("CBS Sports", "https://www.cbssports.com/rss/headlines/nba"),
        ("ESPN", "https://www.espn.com/espn/rss/nba/news")
    ]
    
    for name, url in sources:
        intel_data["cbs_espn"].extend(search_rss_generic(player_name, url, name))
    
    # Check if we have anything concrete
    has_info = False
    if isinstance(intel_data["reddit"], list) and len(intel_data["reddit"]) > 0:
        has_info = True
    if isinstance(intel_data["rotowire"], list) and len(intel_data["rotowire"]) > 0:
        has_info = True
    if len(intel_data["cbs_espn"]) > 0:
        has_info = True
        
    if not has_info:
        intel_data["fallback_suggested"] = True
        intel_data["fallback_reason"] = "No recent specific mentions found in direct feeds."
    
    print(json.dumps(intel_data, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: search_external_intel.py <player_name>"}, indent=2))
        sys.exit(1)

    player_name_arg = " ".join(sys.argv[1:])
    search_external_intel(player_name_arg)
