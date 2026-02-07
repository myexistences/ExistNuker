"""
User Operations Module
- Two modes: Fetch mode and Fast mode
- Kicks bots first (can't ban bots)
- FULL SPEED banning
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, get_bot_info, get_bot_highest_role_position, get_guild_roles, BASE_URL
from config import Colors, THREADS, TIMEOUT


def get_members(token, guild_id, limit=1000, after=None):
    """Get guild members (paginated)"""
    endpoint = f"/guilds/{guild_id}/members?limit={limit}"
    if after:
        endpoint += f"&after={after}"
    
    success, data = make_request("GET", endpoint, token)
    if success and isinstance(data, list):
        return data
    return []


def get_member_highest_role(member, all_roles):
    """Get the highest role position of a member"""
    member_role_ids = member.get('roles', [])
    if not member_role_ids:
        return 0
    
    highest = 0
    for role in all_roles:
        if role.get('id') in member_role_ids:
            pos = role.get('position', 0)
            if pos > highest:
                highest = pos
    return highest


def kick_user_fast(token, guild_id, user_id):
    """Kick a user - FAST, ignore errors"""
    session = get_session()
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    try:
        response = session.delete(f"{BASE_URL}/guilds/{guild_id}/members/{user_id}", headers=headers, timeout=3)
        return response.status_code in [200, 204, 404]
    except Exception:
        return False


def ban_user_fast(token, guild_id, user_id):
    """Ban a user - FAST, ignore errors"""
    session = get_session()
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    try:
        response = session.put(f"{BASE_URL}/guilds/{guild_id}/bans/{user_id}", headers=headers, json={"delete_message_seconds": 0}, timeout=3)
        return response.status_code in [200, 204, 404]
    except Exception:
        return False


def prune_members(token, guild_id, days=7, include_roles=True):
    """Prune inactive members"""
    days = max(1, min(30, days))
    
    endpoint = f"/guilds/{guild_id}/prune?days={days}"
    if include_roles:
        endpoint += "&include_roles=true"
    
    print(f"{Colors.CYAN}Checking prune count for {days} days...{Colors.RESET}")
    success, data = make_request("GET", endpoint, token)
    
    if not success:
        print(f"{Colors.RED}Failed to get prune count{Colors.RESET}")
        return 0
    
    prune_count = data.get('pruned', 0) if data else 0
    print(f"{Colors.CYAN}Members to prune: {prune_count}{Colors.RESET}")
    
    if prune_count == 0:
        print(f"{Colors.YELLOW}No members to prune{Colors.RESET}")
        return 0
    
    print(f"{Colors.RED}Pruning {prune_count} members...{Colors.RESET}")
    payload = {"days": days}
    if include_roles:
        payload["include_roles"] = True
    
    success, data = make_request("POST", f"/guilds/{guild_id}/prune", token, payload)
    
    if success:
        pruned = data.get('pruned', 0) if data else 0
        print(f"{Colors.GREEN}Pruned {pruned} members{Colors.RESET}")
        return pruned
    return 0


def ban_all(token, guild_id, fetch_mode=True, thread_count=THREADS, stop_event=None):
    """
    Ban all members
    
    fetch_mode=True: Fetch 1k -> ban -> fetch again until none left
    fetch_mode=False: Fast mode - ban continuously, pause after 1k, repeat
    """
    bot_info = get_bot_info(token)
    bot_id = bot_info.get('id') if bot_info else None
    
    bot_highest = get_bot_highest_role_position(token, guild_id)
    all_roles = get_guild_roles(token, guild_id)
    
    total_kicked = 0
    total_banned = 0
    
    if fetch_mode:
        # FETCH MODE: Fetch 1k, ban, repeat until no members left
        print(f"{Colors.CYAN}Fetch Mode: Will fetch 1k, ban, fetch again until done{Colors.RESET}")
        
        round_num = 0
        while True:
            if stop_event and stop_event.is_set():
                break
            
            round_num += 1
            print(f"\n{Colors.CYAN}=== Round {round_num}: Fetching up to 1000 members ==={Colors.RESET}")
            
            members = get_members(token, guild_id, limit=1000)
            if not members:
                print(f"{Colors.GREEN}No more members to ban!{Colors.RESET}")
                break
            
            bots = []
            users_list = []
            
            for m in members:
                user = m.get('user', {})
                user_id = user.get('id')
                username = user.get('username', user_id)
                is_bot = user.get('bot', False)
                
                if not user_id or user_id == bot_id:
                    continue
                
                member_highest = get_member_highest_role(m, all_roles)
                if member_highest >= bot_highest:
                    continue
                
                if is_bot:
                    bots.append({'id': user_id, 'name': username})
                else:
                    users_list.append({'id': user_id, 'name': username})
            
            if not bots and not users_list:
                print(f"{Colors.GREEN}No bannable members found!{Colors.RESET}")
                break
            
            print(f"{Colors.CYAN}Found {len(bots)} bots, {len(users_list)} members{Colors.RESET}")
            
            # Kick bots
            for bot in bots:
                if stop_event and stop_event.is_set():
                    break
                if kick_user_fast(token, guild_id, bot['id']):
                    total_kicked += 1
                    print(f"{Colors.MAGENTA}[{total_kicked}] Kicked: {bot['name']}{Colors.RESET}")
            
            # Ban members
            for user in users_list:
                if stop_event and stop_event.is_set():
                    break
                if ban_user_fast(token, guild_id, user['id']):
                    total_banned += 1
                    print(f"{Colors.GREEN}[{total_banned}] Banned: {user['name']}{Colors.RESET}")
            
            print(f"{Colors.YELLOW}Round {round_num} done. Checking for more...{Colors.RESET}")
            time.sleep(1)  # Brief pause before next round
    
    else:
        # FAST MODE: Ban as fast as possible with role checks and loop detection
        print(f"{Colors.CYAN}Fast Mode: Banning at max speed, ignoring errors{Colors.RESET}")
        
        banned_count = [0]
        kicked_count = [0]
        lock = threading.Lock()
        
        # Track already-attempted users to detect infinite loops
        attempted_ids = set()
        
        round_num = 0
        consecutive_no_new = 0  # Track rounds with no new members
        
        while True:
            if stop_event and stop_event.is_set():
                break
            
            round_num += 1
            print(f"\n{Colors.CYAN}=== Round {round_num}: Fetching batch ==={Colors.RESET}")
            
            members = get_members(token, guild_id, limit=1000)
            if not members:
                print(f"{Colors.GREEN}No more members!{Colors.RESET}")
                break
            
            bots = []
            users_list = []
            new_found = False
            
            for m in members:
                user = m.get('user', {})
                user_id = user.get('id')
                is_bot = user.get('bot', False)
                
                if not user_id or user_id == bot_id:
                    continue
                
                # Check role hierarchy (skip if member's role >= bot's role)
                member_highest = get_member_highest_role(m, all_roles)
                if member_highest >= bot_highest:
                    continue
                
                # Skip already attempted
                if user_id in attempted_ids:
                    continue
                
                new_found = True
                
                if is_bot:
                    bots.append({'id': user_id, 'name': user.get('username', user_id)})
                else:
                    users_list.append({'id': user_id, 'name': user.get('username', user_id)})
            
            if not bots and not users_list:
                if not new_found:
                    consecutive_no_new += 1
                    if consecutive_no_new >= 2:
                        print(f"{Colors.GREEN}No new bannable members found (all remaining have higher roles)!{Colors.RESET}")
                        break
                    print(f"{Colors.YELLOW}No new members in this batch, checking again...{Colors.RESET}")
                    time.sleep(1)
                    continue
                print(f"{Colors.GREEN}No bannable members!{Colors.RESET}")
                break
            
            consecutive_no_new = 0  # Reset counter when we find new members
            
            # Mark all as attempted
            for bot in bots:
                attempted_ids.add(bot['id'])
            for user in users_list:
                attempted_ids.add(user['id'])
            
            print(f"{Colors.RED}Banning {len(bots)} bots + {len(users_list)} members FAST...{Colors.RESET}")
            
            def fast_kick_worker(bot_list):
                for bot in bot_list:
                    if stop_event and stop_event.is_set():
                        return
                    kick_user_fast(token, guild_id, bot['id'])
                    with lock:
                        kicked_count[0] += 1
                    print(f"{Colors.MAGENTA}[{kicked_count[0]}] Kicked: {bot['name']}{Colors.RESET}")
            
            def fast_ban_worker(user_list):
                for user in user_list:
                    if stop_event and stop_event.is_set():
                        return
                    ban_user_fast(token, guild_id, user['id'])
                    with lock:
                        banned_count[0] += 1
                    print(f"{Colors.GREEN}[{banned_count[0]}] Banned: {user['name']}{Colors.RESET}")
            
            # Multi-threaded fast banning
            threads = []
            
            # Kick bots with threads
            if bots:
                safe_threads = min(20, len(bots))
                per_thread = max(1, len(bots) // safe_threads)
                for i in range(0, len(bots), per_thread):
                    chunk = bots[i:i+per_thread]
                    t = threading.Thread(target=fast_kick_worker, args=(chunk,))
                    threads.append(t)
                    t.start()
            
            # Ban users with threads
            if users_list:
                safe_threads = min(30, len(users_list))
                per_thread = max(1, len(users_list) // safe_threads)
                for i in range(0, len(users_list), per_thread):
                    chunk = users_list[i:i+per_thread]
                    t = threading.Thread(target=fast_ban_worker, args=(chunk,))
                    threads.append(t)
                    t.start()
            
            for t in threads:
                t.join()
            
            total_kicked = kicked_count[0]
            total_banned = banned_count[0]
            
            print(f"{Colors.YELLOW}Processed batch. Pausing 1s before next...{Colors.RESET}")
            time.sleep(1)
    
    print(f"\n{Colors.GREEN}Finished! Kicked {total_kicked} bots, Banned {total_banned} members{Colors.RESET}")
    return total_kicked + total_banned

