"""
Role Operations Module
- Skips roles above bot
- Skips managed/bot-specific roles
- Rate limit handling
- Live Status Updates (Success/Fail counts)
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, BASE_URL, get_bot_highest_role_position, get_guild_roles
from config import THREADS, TIMEOUT, stop_event
from interface import ui

def get_all(token, guild_id, check_hierarchy=False):
    """
    Get all deletable roles in a guild
    """
    with ui.status_spinner("Fetching all roles..."):
        all_roles = get_guild_roles(token, guild_id)
        
        if not all_roles:
            return []
        
        # Get bot's highest role position
        bot_highest = 0
        if check_hierarchy:
            bot_highest = get_bot_highest_role_position(token, guild_id)
    
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
            continue
        
        # Skip roles above bot
        if check_hierarchy and r.get('position', 0) >= bot_highest:
            skipped_above += 1
            continue
        
        roles.append(r)
    
    ui.print_info(f"Found {len(roles)} deletable roles")
    if skipped_managed > 0:
        ui.print_logs(f"Skipped {skipped_managed} bot-specific roles")
    if skipped_above > 0:
        ui.print_logs(f"Skipped {skipped_above} roles above bot")
    
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
    """Create multiple roles with live stats"""
    count = min(500, count)
    created = [0]
    failed = [0]
    lock = threading.Lock()
    
    ui.print_info(f"Creating {count} roles named '{name}'...")
    
    def worker(num_to_create):
        for _ in range(num_to_create):
            if stop_event and stop_event.is_set():
                return
            success, data = create(token, guild_id, name, color)
            if success:
                with lock:
                    created[0] += 1
                    ui.console.print(f"[green]✓[/green] Created: [magenta]{name}[/magenta] ({created[0]}/{count})")
            else:
                with lock:
                    failed[0] += 1
                    ui.console.print(f"[red]✗[/red] Failed to create role")
    
    threads = []
    per_thread = max(1, count // thread_count)
    
    for i in range(0, count, per_thread):
        if stop_event and stop_event.is_set():
            break
        num = min(per_thread, count - i)
        t = threading.Thread(target=worker, args=(num,), daemon=True)
        threads.append(t)
        t.start()
    
    while any(t.is_alive() for t in threads):
        if stop_event.is_set():
            return 0
        time.sleep(0.1)
    
    ui.print_success(f"Created {created[0]} roles | Failed {failed[0]}")
    return created[0]


def nuke(token, guild_id, thread_count=THREADS, stop_event=None):
    """Delete ALL deletable roles with live stats"""
    all_roles = get_all(token, guild_id, check_hierarchy=True)
    if not all_roles:
        ui.print_warning("No deletable roles found")
        return 0
    
    total = len(all_roles)
    ui.print_warning(f"Deleting {total} roles...")
    
    deleted = [0]
    failed_count = [0]
    failed_roles = []
    lock = threading.Lock()
    
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
                    ui.console.print(f"[green]✓[/green] Deleted: [cyan]{role_name}[/cyan] ({deleted[0]}/{total})")
            else:
                with lock:
                    failed_count[0] += 1
                    failed_roles.append(role)
                    ui.console.print(f"[red]✗[/red] Failed: [yellow]{role_name}[/yellow]")
            
            if stop_event.wait(0.05):
                return
    
    threads = []
    per_thread = max(1, len(all_roles) // safe_threads)
    
    for i in range(0, len(all_roles), per_thread):
        if stop_event and stop_event.is_set():
            break
        chunk = all_roles[i:i+per_thread]
        t = threading.Thread(target=worker, args=(chunk,), daemon=True)
        threads.append(t)
        t.start()
    
    while any(t.is_alive() for t in threads):
        if stop_event.is_set():
            return 0
        time.sleep(0.1)
    
    # Retry failed roles
    if failed_roles and (not stop_event or not stop_event.is_set()):
        ui.print_warning(f"Retrying {len(failed_roles)} failed roles...")
        
        for role in failed_roles[:]:
            if stop_event and stop_event.is_set():
                break
            
            role_id = role.get('id')
            role_name = role.get('name', 'unknown')
            
            if stop_event.wait(0.5):
                break
            
            if delete_role(token, guild_id, role_id, max_retries=5):
                deleted[0] += 1
                failed_count[0] -= 1
                ui.console.print(f"[green]✓[/green] Retry Success: [cyan]{role_name}[/cyan]")
            else:
                ui.console.print(f"[red]✗[/red] Retry Failed: [yellow]{role_name}[/yellow]")
    
    ui.print_success(f"Finished! Deleted {deleted[0]}/{total} roles")
    return deleted[0]
