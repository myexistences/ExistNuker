"""
Role Operations Module
- Skips roles above bot
- Skips managed/bot-specific roles
- Rate limit handling
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, BASE_URL, get_bot_highest_role_position, get_guild_roles
from config import Colors, THREADS, TIMEOUT, stop_event


def get_all(token, guild_id, check_hierarchy=False):
    """
    Get all deletable roles in a guild
    Skips:
    - @everyone
    - Managed roles (bot-specific roles)
    - Roles above bot's highest role
    """
    print(f"{Colors.CYAN}Fetching all roles...{Colors.RESET}")
    
    all_roles = get_guild_roles(token, guild_id)
    if not all_roles:
        return []
    
    # Get bot's highest role position
    bot_highest = 0
    if check_hierarchy:
        bot_highest = get_bot_highest_role_position(token, guild_id)
        print(f"{Colors.CYAN}Bot's highest role position: {bot_highest}{Colors.RESET}")
    
    # Filter roles
    roles = []
    skipped_above = 0
    skipped_managed = 0
    
    for r in all_roles:
        role_name = r.get('name', 'unknown')
        
        # Skip @everyone
        if role_name == '@everyone':
            continue
        
        # Skip managed roles (bot-specific roles)
        if r.get('managed', False):
            skipped_managed += 1
            print(f"{Colors.YELLOW}Skipping (bot role): {role_name}{Colors.RESET}")
            continue
        
        # Skip roles above bot
        if check_hierarchy and r.get('position', 0) >= bot_highest:
            skipped_above += 1
            print(f"{Colors.YELLOW}Skipping (above bot): {role_name}{Colors.RESET}")
            continue
        
        roles.append(r)
    
    print(f"{Colors.CYAN}Found {len(roles)} deletable roles{Colors.RESET}")
    if skipped_managed > 0:
        print(f"{Colors.YELLOW}Skipped {skipped_managed} bot-specific roles{Colors.RESET}")
    if skipped_above > 0:
        print(f"{Colors.YELLOW}Skipped {skipped_above} roles above bot{Colors.RESET}")
    
    return roles


def create(token, guild_id, name, color=0x6B00FF):
    """Create a role in a guild"""
    payload = {"name": name, "color": color}
    success, data = make_request("POST", f"/guilds/{guild_id}/roles", token, payload)
    return success, data


def delete_role(token, guild_id, role_id, max_retries=5):
    """Delete a single role with rate limit handling"""
    session = get_session()
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    timeout_seconds = TIMEOUT / 1000 if TIMEOUT else 10
    
    for attempt in range(max_retries):
        try:
            response = session.delete(
                f"{BASE_URL}/guilds/{guild_id}/roles/{role_id}",
                headers=headers,
                timeout=timeout_seconds
            )
            
            if response.status_code in [200, 204]:
                return True
            
            if response.status_code == 404:
                return True  # Already deleted
            
            if response.status_code == 429:
                try:
                    data = response.json()
                    retry_after = data.get("retry_after", 1)
                except Exception:
                    retry_after = 1
                if stop_event.wait(retry_after + 0.1):
                    return False
                continue
            
            if response.status_code in [400, 403]:
                return False  # Can't delete
            
            if stop_event.wait(0.2):
                return False
            
        except Exception:
            if stop_event.wait(0.2):
                return False
            continue
    
    return False


def spam(token, guild_id, name, count, color=0x6B00FF, thread_count=THREADS, stop_event=None):
    """Create multiple roles"""
    created = [0]
    lock = threading.Lock()
    
    print(f"{Colors.CYAN}Creating {count} roles named '{name}'...{Colors.RESET}")
    
    def worker(num_to_create):
        for _ in range(num_to_create):
            if stop_event and stop_event.is_set():
                return
            success, data = create(token, guild_id, name, color)
            if success:
                with lock:
                    created[0] += 1
                print(f"{Colors.GREEN}Created {Colors.WHITE}{name}{Colors.RESET}")
            else:
                error = data.get('message', 'Unknown') if data else 'Unknown'
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
    
    print(f"{Colors.GREEN}Created {created[0]} roles{Colors.RESET}")
    return created[0]


def nuke(token, guild_id, thread_count=THREADS, stop_event=None):
    """Delete ALL deletable roles (skips bot roles and roles above bot)"""
    # Fetch roles with hierarchy check
    all_roles = get_all(token, guild_id, check_hierarchy=True)
    if not all_roles:
        print(f"{Colors.YELLOW}No deletable roles found{Colors.RESET}")
        return 0
    
    total = len(all_roles)
    print(f"{Colors.RED}Deleting {total} roles...{Colors.RESET}")
    
    deleted = [0]
    failed_roles = []
    lock = threading.Lock()
    
    # Use limited threads
    safe_threads = min(thread_count, 10)
    
    def worker(role_list):
        for role in role_list:
            if stop_event and stop_event.is_set():
                return
            
            role_id = role.get('id')
            role_name = role.get('name', 'unknown')
            
            if delete_role(token, guild_id, role_id, max_retries=3):
                with lock:
                    deleted[0] += 1
                print(f"{Colors.GREEN}Deleted {Colors.WHITE}{role_name}{Colors.RESET}")
            else:
                with lock:
                    failed_roles.append(role)
                print(f"{Colors.RED}Failed: {role_name}{Colors.RESET}")
            
            if stop_event.wait(0.1):
                return
    
    # First pass
    threads = []
    per_thread = max(1, len(all_roles) // safe_threads)
    
    for i in range(0, len(all_roles), per_thread):
        if stop_event and stop_event.is_set():
            break
        chunk = all_roles[i:i+per_thread]
        t = threading.Thread(target=worker, args=(chunk,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Retry failed roles
    if failed_roles and (not stop_event or not stop_event.is_set()):
        print(f"\n{Colors.YELLOW}Retrying {len(failed_roles)} failed roles...{Colors.RESET}")
        
        for role in failed_roles[:]:
            if stop_event and stop_event.is_set():
                break
            
            role_id = role.get('id')
            role_name = role.get('name', 'unknown')
            
            if stop_event.wait(0.5):
                break
            
            if delete_role(token, guild_id, role_id, max_retries=5):
                deleted[0] += 1
                print(f"{Colors.GREEN}Deleted {role_name}{Colors.RESET}")
    
    print(f"\n{Colors.GREEN}Finished! Deleted {deleted[0]}/{total} roles{Colors.RESET}")
    return deleted[0]
