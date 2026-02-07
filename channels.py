"""
Channel Operations Module
Handles Discord channel CRUD operations with retry logic
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, BASE_URL
from config import Colors, THREADS, TIMEOUT, stop_event


class ChannelType:
    TEXT = 0
    VOICE = 2
    CATEGORY = 4
    STAGE = 13


def get_all(token, guild_id):
    """Get all channels in a guild (including categories)"""
    print(f"{Colors.CYAN}Fetching all channels...{Colors.RESET}")
    success, data = make_request("GET", f"/guilds/{guild_id}/channels", token)
    if success and isinstance(data, list):
        print(f"{Colors.CYAN}Found {len(data)} channels{Colors.RESET}")
        return data
    return []


def create(token, guild_id, name, channel_type=ChannelType.TEXT):
    """Create a channel in a guild"""
    payload = {
        "name": name,
        "type": channel_type
    }
    
    # Only text channels support topic
    if channel_type == ChannelType.TEXT:
        payload["topic"] = "Created by ExistNuker"
    
    success, data = make_request("POST", f"/guilds/{guild_id}/channels", token, payload)
    return success, data


def delete(token, channel_id, max_retries=5):
    """
    Delete a channel with retry logic for rate limits
    Returns: (success: bool, skip: bool) - skip=True means channel can't be deleted
    """
    session = get_session()
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    timeout_seconds = TIMEOUT / 1000 if TIMEOUT else 10
    
    for attempt in range(max_retries):
        try:
            response = session.delete(
                f"{BASE_URL}/channels/{channel_id}",
                headers=headers,
                timeout=timeout_seconds
            )
            
            if response.status_code == 204 or response.status_code == 200:
                return True, False
            
            if response.status_code == 429:
                # Rate limited - wait and retry
                try:
                    data = response.json()
                    retry_after = data.get("retry_after", 1)
                except Exception:
                    retry_after = 1
                if stop_event.wait(retry_after):
                    return False, False
                continue
            
            if response.status_code == 404:
                # Already deleted
                return True, False
            
            # Check for non-deletable channels (community, rules, etc)
            if response.status_code == 400 or response.status_code == 403:
                try:
                    data = response.json()
                    error_code = data.get("code", 0)
                    message = data.get("message", "")
                    
                    # Error codes for non-deletable channels:
                    # 50074 - Cannot delete a channel required for Community Servers
                    # 50035 - Invalid Form Body (usually system channel)
                    # 50013 - Missing Permissions
                    if error_code in [50074, 50035, 50013] or "community" in message.lower() or "cannot delete" in message.lower():
                        return False, True  # Skip this channel
                except Exception:
                    pass
            
            if stop_event.wait(0.5):
                return False, False
            
        except Exception:
            if stop_event.wait(0.5):
                return False, False
            continue
    
    return False, False


def spam(token, guild_id, name, channel_type, count, thread_count=THREADS, stop_event=None):
    """Create multiple channels using threading"""
    count = min(500, count)
    created = [0]
    lock = threading.Lock()
    
    print(f"{Colors.CYAN}Creating {count} channels named '{name}'...{Colors.RESET}")
    
    def worker(num_to_create):
        for _ in range(num_to_create):
            if stop_event and stop_event.is_set():
                return
            success, data = create(token, guild_id, name, channel_type)
            if success:
                with lock:
                    created[0] += 1
                channel_id = data.get('id', 'unknown')
                print(f"{Colors.GREEN}Created {Colors.WHITE}#{name}{Colors.RESET} [{channel_id}]")
            else:
                error = data.get('message', 'Unknown error') if data else 'Unknown error'
                print(f"{Colors.RED}Failed: {error}{Colors.RESET}")
    
    threads = []
    per_thread = max(1, count // thread_count)
    
    for i in range(0, count, per_thread):
        if stop_event and stop_event.is_set():
            break
        num = min(per_thread, count - i)
        t = threading.Thread(target=worker, args=(num,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"{Colors.GREEN}Created {created[0]} channels{Colors.RESET}")
    return created[0]


def nuke(token, guild_id, thread_count=THREADS, stop_event=None):
    """
    Delete ALL channels and categories in a guild
    Skips community/system channels that can't be deleted
    """
    # Fetch all channels first
    all_channels = get_all(token, guild_id)
    if not all_channels:
        print(f"{Colors.YELLOW}No channels found{Colors.RESET}")
        return 0
    
    total = len(all_channels)
    print(f"{Colors.RED}Deleting {total} channels/categories...{Colors.RESET}")
    
    deleted = [0]
    skipped = [0]
    failed_channels = []
    lock = threading.Lock()
    
    def worker(channel_list):
        for channel in channel_list:
            if stop_event and stop_event.is_set():
                return
            
            channel_id = channel.get('id')
            channel_name = channel.get('name', 'unknown')
            channel_type = channel.get('type', 0)
            
            type_str = "category" if channel_type == 4 else "channel"
            
            success, skip = delete(token, channel_id)
            
            if success:
                with lock:
                    deleted[0] += 1
                print(f"{Colors.GREEN}Deleted {type_str} {Colors.WHITE}#{channel_name}{Colors.RESET}")
            elif skip:
                with lock:
                    skipped[0] += 1
                print(f"{Colors.YELLOW}Skipped (community/system): #{channel_name}{Colors.RESET}")
            else:
                with lock:
                    failed_channels.append(channel)
                print(f"{Colors.RED}Failed: #{channel_name}{Colors.RESET}")
    
    # First pass - try to delete all channels
    threads = []
    per_thread = max(1, len(all_channels) // thread_count)
    
    for i in range(0, len(all_channels), per_thread):
        if stop_event and stop_event.is_set():
            break
        chunk = all_channels[i:i+per_thread]
        t = threading.Thread(target=worker, args=(chunk,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Second pass - retry failed channels one by one
    if failed_channels and (not stop_event or not stop_event.is_set()):
        print(f"\n{Colors.YELLOW}Retrying {len(failed_channels)} failed channels...{Colors.RESET}")
        
        for channel in failed_channels[:]:
            if stop_event and stop_event.is_set():
                break
            
            channel_id = channel.get('id')
            channel_name = channel.get('name', 'unknown')
            
            success, skip = delete(token, channel_id, max_retries=10)
            if success:
                deleted[0] += 1
                failed_channels.remove(channel)
                print(f"{Colors.GREEN}Deleted #{channel_name}{Colors.RESET}")
            elif skip:
                skipped[0] += 1
                failed_channels.remove(channel)
                print(f"{Colors.YELLOW}Skipped (community/system): #{channel_name}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Still failed: #{channel_name}{Colors.RESET}")
    
    print(f"\n{Colors.GREEN}Finished! Deleted {deleted[0]}/{total} channels{Colors.RESET}")
    if skipped[0] > 0:
        print(f"{Colors.YELLOW}Skipped {skipped[0]} community/system channels{Colors.RESET}")
    return deleted[0]
