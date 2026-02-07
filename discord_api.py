"""
Discord API Utilities
Base module for Discord REST API interactions
Cross-platform with connection pooling
"""

import requests
import time
from config import TIMEOUT, Colors, stop_event

BASE_URL = "https://discord.com/api/v9"

# Shared session for connection pooling
_session = None


def get_session():
    """Get or create shared requests session for connection reuse"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "Content-Type": "application/json"
        })
    return _session


def make_request(method, endpoint, token, json_data=None, max_retries=3):
    """Make a Discord API request with rate limit handling"""
    session = get_session()
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}{endpoint}"
    timeout_seconds = TIMEOUT / 1000 if TIMEOUT else 10
    
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                response = session.get(url, headers=headers, timeout=timeout_seconds)
            elif method.upper() == "POST":
                response = session.post(url, headers=headers, json=json_data, timeout=timeout_seconds)
            elif method.upper() == "DELETE":
                response = session.delete(url, headers=headers, timeout=timeout_seconds)
            elif method.upper() == "PUT":
                response = session.put(url, headers=headers, json=json_data, timeout=timeout_seconds)
            elif method.upper() == "PATCH":
                response = session.patch(url, headers=headers, json=json_data, timeout=timeout_seconds)
            else:
                return False, {"error": f"Unknown method: {method}"}
            
            if response.status_code == 429:
                data = response.json()
                retry_after = data.get("retry_after", 1)
                if stop_event.wait(retry_after):
                    return False, {"error": "Interrupted"}
                continue
            
            if response.status_code in [200, 201, 204]:
                if response.status_code == 204:
                    return True, None
                return True, response.json()
            
            try:
                data = response.json()
                # Check for "Unknown Guild" or similar errors indicating bot kicked
                if isinstance(data, dict):
                    code = data.get("code")
                    if code == 10004:  # Unknown Guild
                        from config import kicked_event
                        if not kicked_event.is_set():
                            kicked_event.set()
                            stop_event.set() # Stop operation immediately
                        return False, {"error": "Bot Kicked"}
                
                return False, data
            except Exception:
                return False, {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}
    
    return False, {"error": "Max retries exceeded"}


def test_token(token):
    """Test if a bot token is valid"""
    success, data = make_request("GET", "/users/@me", token)
    return success


def is_in_guild(token, guild_id):
    """Check if bot is in a guild"""
    success, data = make_request("GET", f"/guilds/{guild_id}", token)
    return success


def leave_guild(token, guild_id):
    """Make the bot leave a guild"""
    # Bots use this endpoint to leave guilds
    success, data = make_request("DELETE", f"/guilds/{guild_id}/members/@me", token)
    return success


def get_bot_info(token):
    """Get bot user information"""
    success, data = make_request("GET", "/users/@me", token)
    return data if success else None


def get_bot_guilds(token):
    """Get all guilds the bot is in"""
    success, data = make_request("GET", "/users/@me/guilds", token)
    if success and isinstance(data, list):
        return data
    return []


def get_guild_info(token, guild_id):
    """Get detailed guild information"""
    success, data = make_request("GET", f"/guilds/{guild_id}?with_counts=true", token)
    return data if success else None


def get_guild_bans(token, guild_id):
    """Get guild ban list"""
    success, data = make_request("GET", f"/guilds/{guild_id}/bans?limit=1000", token)
    if success and isinstance(data, list):
        return data
    return []


def get_guild_channels(token, guild_id):
    """Get all channels in a guild"""
    success, data = make_request("GET", f"/guilds/{guild_id}/channels", token)
    if success and isinstance(data, list):
        return data
    return []


def get_guild_roles(token, guild_id):
    """Get all roles in a guild"""
    success, data = make_request("GET", f"/guilds/{guild_id}/roles", token)
    if success and isinstance(data, list):
        return data
    return []


def get_bot_member(token, guild_id):
    """Get the bot's member object in a guild (includes roles)"""
    bot_info = get_bot_info(token)
    if not bot_info:
        return None
    
    bot_id = bot_info.get('id')
    success, data = make_request("GET", f"/guilds/{guild_id}/members/{bot_id}", token)
    return data if success else None


def get_bot_highest_role_position(token, guild_id):
    """Get the position of the bot's highest role"""
    bot_member = get_bot_member(token, guild_id)
    if not bot_member:
        return 0
    
    bot_role_ids = bot_member.get('roles', [])
    if not bot_role_ids:
        return 0
    
    # Get all roles to find positions
    all_roles = get_guild_roles(token, guild_id)
    if not all_roles:
        return 0
    
    # Find highest position among bot's roles
    highest = 0
    for role in all_roles:
        if role.get('id') in bot_role_ids:
            pos = role.get('position', 0)
            if pos > highest:
                highest = pos
    
    return highest
