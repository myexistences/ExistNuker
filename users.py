"""
User Operations Module
- Two modes: Fetch mode and Fast mode
- Kicks bots first (can't ban bots)
- FULL SPEED banning
- Live Status Updates (Banned/Failed counts)
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, get_bot_info, get_bot_highest_role_position, get_guild_roles, BASE_URL
from config import THREADS, TIMEOUT
from interface import ui

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
    """Kick a user - FAST with one retry"""
    session = get_session()
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    for _ in range(2): # 1 retry
        try:
            response = session.delete(f"{BASE_URL}/guilds/{guild_id}/members/{user_id}", headers=headers, timeout=5)
            if response.status_code in [200, 204, 404]:
                return True
            if response.status_code == 429:
                time.sleep(response.json().get("retry_after", 1))
        except Exception:
            pass
    return False

def ban_user_fast(token, guild_id, user_id):
    """Ban a user - FAST with one retry"""
    session = get_session()
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"delete_message_seconds": 0}
    for _ in range(2): # 1 retry
        try:
            response = session.put(f"{BASE_URL}/guilds/{guild_id}/bans/{user_id}", headers=headers, json=payload, timeout=5)
            if response.status_code in [200, 204, 404]:
                return True
            if response.status_code == 429:
                time.sleep(response.json().get("retry_after", 1))
        except Exception:
            pass
    return False

def prune_members(token, guild_id, days=7, include_roles=True):
    """Prune inactive members"""
    days = max(1, min(30, days))
    
    endpoint = f"/guilds/{guild_id}/prune?days={days}"
    if include_roles:
        endpoint += "&include_roles=true"
    
    with ui.status_spinner(f"Checking prune count for {days} days..."):
        success, data = make_request("GET", endpoint, token)
    
    if not success:
        ui.print_error("Failed to get prune count")
        return 0
    
    prune_count = data.get('pruned', 0) if data else 0
    ui.print_info(f"Members to prune: {prune_count}")
    
    if prune_count == 0:
        ui.print_warning("No members to prune")
        return 0
    
    payload = {"days": days}
    if include_roles:
        payload["include_roles"] = True
    
    with ui.status_spinner(f"Pruning {prune_count} members..."):
        success, data = make_request("POST", f"/guilds/{guild_id}/prune", token, payload)
    
    if success:
        pruned = data.get('pruned', 0) if data else 0
        ui.print_success(f"Pruned {pruned} members")
        return pruned
    return 0

def ban_all(token, guild_id, fetch_mode=True, thread_count=THREADS, stop_event=None):
    """
    Ban all members
    Using rich progress bars with Live Stats
    """
    bot_info = get_bot_info(token)
    bot_id = bot_info.get('id') if bot_info else None
    
    with ui.status_spinner("Fetching role data..."):
        bot_highest = get_bot_highest_role_position(token, guild_id)
        all_roles = get_guild_roles(token, guild_id)
    
    total_kicked = 0
    total_banned = 0
    total_failed = 0
    
    if fetch_mode:
        ui.print_info("Fetch Mode: Will fetch 1k, ban, fetch again until done")
        
        round_num = 0
        while True:
            if stop_event and stop_event.is_set():
                break
            
            round_num += 1
            ui.print_info(f"=== Round {round_num}: Fetching up to 1000 members ===")
            
            with ui.status_spinner("Fetching members..."):
                members = get_members(token, guild_id, limit=1000)
            
            if not members:
                ui.print_success("No more members to ban!")
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
                ui.print_success("No bannable members found in this batch!")
                break
            
            ui.print_info(f"Found {len(bots)} bots, {len(users_list)} members")
            
            # Use progress bar for actions
            with ui.progress_bar(description="Processing batch...") as progress:
                kick_task = progress.add_task("[magenta]Kicking Bots...", total=len(bots)) if bots else None
                ban_task = progress.add_task("[red]Banning Members...", total=len(users_list)) if users_list else None
                
                # Kick bots
                for bot in bots:
                    if stop_event and stop_event.is_set(): break
                    success = kick_user_fast(token, guild_id, bot['id'])
                    if success:
                        total_kicked += 1
                        progress.update(kick_task, advance=1, description=f"[magenta]Kicked: {bot['name']} | Total: {total_kicked}[/magenta]")
                    else:
                        total_failed += 1
                        progress.update(kick_task, advance=1, description=f"[red]Failed: {bot['name']}")
                
                # Ban members
                for user in users_list:
                    if stop_event and stop_event.is_set(): break
                    success = ban_user_fast(token, guild_id, user['id'])
                    if success:
                        total_banned += 1
                        progress.update(ban_task, advance=1, description=f"[red]Banned: {user['name']} | Total: {total_banned}[/red]")
                    else:
                        total_failed += 1
                        progress.update(ban_task, advance=1, description=f"[yellow]Failed: {user['name']}")
            
            ui.print_warning(f"Round {round_num} done. Caught {total_banned} bans, {total_kicked} kicks.")
            time.sleep(1)
    
    else:
        # FAST MODE
        ui.print_info("Fast Mode: Banning at max speed")
        
        banned_count = [0]
        kicked_count = [0]
        failed_count = [0]
        lock = threading.Lock()
        attempted_ids = set()
        
        round_num = 0
        last_id = None
        
        while True:
            if stop_event and stop_event.is_set(): break
            round_num += 1
            
            with ui.status_spinner(f"Round {round_num}: Fetching members..."):
                members = get_members(token, guild_id, limit=1000, after=last_id)
            
            if not members:
                if last_id is not None:
                    # Reached end of list, loop back to check for missed targets
                    last_id = None
                    continue
                ui.print_success("No more members!")
                break
            
            # Update last_id for next page
            last_id = members[-1]['user']['id']
            
            bots = []
            users_list = []
            new_found = False
            
            for m in members:
                user = m.get('user', {})
                user_id = user.get('id')
                is_bot = user.get('bot', False)
                if not user_id or user_id == bot_id: continue
                
                # Check cache first (Fastest)
                if user_id in attempted_ids: continue
                
                new_found = True
                
                # Check hierarchy (Slower)
                if get_member_highest_role(m, all_roles) >= bot_highest:
                    # Mark unbannable users as attempted so we don't check roles again
                    attempted_ids.add(user_id)
                    continue
                
                if is_bot:
                    bots.append({'id': user_id, 'name': user.get('username', user_id)})
                else:
                    users_list.append({'id': user_id, 'name': user.get('username', user_id)})
                    
            if not bots and not users_list:
                if not new_found:
                    consecutive_no_new += 1
                    if consecutive_no_new >= 2: break
                    time.sleep(1)
                    continue
                break
            
            consecutive_no_new = 0
            for bot in bots: attempted_ids.add(bot['id'])
            for user in users_list: attempted_ids.add(user['id'])
            
            with ui.progress_bar(description="Processing batch...") as progress:
                kick_task = progress.add_task("[magenta]Kicking...", total=len(bots)) if bots else None
                ban_task = progress.add_task("[red]Banning...", total=len(users_list)) if users_list else None
                
                def fast_kick_worker(bot_list):
                    for bot in bot_list:
                        if stop_event.is_set(): return
                        if kick_user_fast(token, guild_id, bot['id']):
                            with lock:
                                kicked_count[0] += 1
                                if kick_task is not None:
                                    progress.update(kick_task, advance=1, description=f"[magenta]Kicked {bot['name']} ({kicked_count[0]})[/magenta]")
                        else:
                            with lock:
                                failed_count[0] += 1
                                if kick_task is not None:
                                    progress.update(kick_task, advance=1)
                
                def fast_ban_worker(user_list):
                    for user in user_list:
                        if stop_event.is_set(): return
                        if ban_user_fast(token, guild_id, user['id']):
                            with lock:
                                banned_count[0] += 1
                                if ban_task is not None:
                                    progress.update(ban_task, advance=1, description=f"[red]Banned {user['name']} ({banned_count[0]})[/red]")
                        else:
                            with lock:
                                failed_count[0] += 1
                                if ban_task is not None:
                                    progress.update(ban_task, advance=1)
                
                threads = []
                if bots:
                    per_thread = max(1, len(bots) // min(20, len(bots)))
                    for i in range(0, len(bots), per_thread):
                        t = threading.Thread(target=fast_kick_worker, args=(bots[i:i+per_thread],), daemon=True)
                        threads.append(t)
                        t.start()
                
                if users_list:
                    per_thread = max(1, len(users_list) // min(30, len(users_list)))
                    for i in range(0, len(users_list), per_thread):
                        t = threading.Thread(target=fast_ban_worker, args=(users_list[i:i+per_thread],), daemon=True)
                        threads.append(t)
                        t.start()
                
                # Non-blocking join
                while any(t.is_alive() for t in threads):
                    if stop_event.is_set():
                        return # Immediately return to menu
                    time.sleep(0.1)
                
                total_kicked = kicked_count[0]
                total_banned = banned_count[0]
                total_failed = failed_count[0]
            
            time.sleep(1)
    
    ui.print_success(f"Finished! Kicked: {total_kicked} | Banned: {total_banned} | Failed: {total_failed}")
    return total_kicked + total_banned
