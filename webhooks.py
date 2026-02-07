"""
Webhook Operations Module
- Handles Discord webhook operations
- Creates webhooks and starts spamming immediately (parallel)
- Supports custom name and avatar with validation
- Live Status Updates (Created/Sent counts)
Cross-platform with connection pooling
"""

import threading
import time
import queue
from discord_api import make_request, get_session
from config import Colors, THREADS, stop_event
import channels
from interface import ui

# Default webhook settings
DEFAULT_WEBHOOK_NAME = "ExistNuker"
DEFAULT_WEBHOOK_AVATAR = "https://i.pinimg.com/originals/a5/4b/a2/a54ba238b3d4843e0dcd3294d168fbca.gif"


def validate_image_url(url):
    """
    Validate if URL is a valid image/gif
    Returns True if valid, False otherwise
    """
    if not url or not url.startswith(('http://', 'https://')):
        return False
    
    session = get_session()
    try:
        # Make HEAD request to check content type
        response = session.head(url, timeout=5, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Check if it's an image
        if any(img_type in content_type for img_type in ['image/', 'gif']):
            return True
        
        # Some URLs don't return proper content-type, try GET with range
        response = session.get(url, timeout=5, stream=True, headers={'Range': 'bytes=0-100'})
        content_type = response.headers.get('Content-Type', '').lower()
        
        if any(img_type in content_type for img_type in ['image/', 'gif']):
            return True
        
        # Check common image extensions
        if any(url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            return response.status_code in [200, 206]
        
        return False
    except Exception:
        return False


def get_channel_webhooks(token, channel_id):
    """Get webhooks for a specific channel"""
    success, data = make_request("GET", f"/channels/{channel_id}/webhooks", token)
    if success and isinstance(data, list):
        return data
    return []


def create(token, channel_id, name):
    """Create a webhook in a channel"""
    payload = {"name": name}
    success, data = make_request("POST", f"/channels/{channel_id}/webhooks", token, payload)
    return success, data


def send(webhook_url, content, username, avatar_url):
    """Send a message via webhook"""
    session = get_session()
    payload = {
        "content": content,
        "username": username,
        "avatar_url": avatar_url
    }
    
    try:
        response = session.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 429:
            try:
                data = response.json()
                retry_after = data.get("retry_after", 1)
                if stop_event.wait(retry_after):
                    return False
                response = session.post(webhook_url, json=payload, timeout=5)
            except Exception:
                pass
        return response.status_code in [200, 204]
    except Exception:
        return False


def get_or_create_webhook(token, channel_id, channel_name, webhook_name):
    """Get existing webhook or create new one"""
    existing = get_channel_webhooks(token, channel_id)
    for wh in existing:
        if wh.get('name') == webhook_name:
            wh_id = wh.get('id')
            wh_token = wh.get('token')
            if wh_id and wh_token:
                return f"https://discord.com/api/webhooks/{wh_id}/{wh_token}"
    
    success, data = create(token, channel_id, webhook_name)
    if success and data:
        wh_id = data.get('id')
        wh_token = data.get('token')
        if wh_id and wh_token:
            return f"https://discord.com/api/webhooks/{wh_id}/{wh_token}"
    
    return None


def spam(token, guild_id, content, amount_per_channel, webhook_name=None, avatar_url=None, thread_count=THREADS, stop_event=None):
    """
    Spam messages - starts spamming immediately as webhooks are created
    """
    # Use defaults if not provided
    name = webhook_name if webhook_name else DEFAULT_WEBHOOK_NAME
    avatar = avatar_url if avatar_url else DEFAULT_WEBHOOK_AVATAR
    
    with ui.status_spinner("Fetching channels..."):
        all_channels = channels.get_all(token, guild_id)
        
    target_channels = [c for c in all_channels if c.get('type', 0) in [0, 2, 5, 13]]
    
    if not target_channels:
        ui.print_warning("No channels found")
        return 0
    
    ui.print_info(f"Found {len(target_channels)} channels")
    ui.print_info(f"Webhook Name: {name}")
    ui.print_info(f"Spamming {amount_per_channel} messages per channel")
    
    webhook_queue = queue.Queue()
    sent = [0]
    created_count = [0]
    failed_create = [0]
    done_creating = [False]
    lock = threading.Lock()
    
    with ui.progress_bar(description="Webhook Spam...") as progress:
        create_task = progress.add_task("[cyan]Creating Webhooks...", total=len(target_channels))
        spam_task = progress.add_task("[magenta]Sending Messages...", total=len(target_channels) * amount_per_channel)
        
        def spam_worker():
            while True:
                if stop_event and stop_event.is_set():
                    return
                
                try:
                    wh = webhook_queue.get(timeout=0.5)
                except queue.Empty:
                    if done_creating[0] and webhook_queue.empty():
                        return
                    continue
                
                for _ in range(amount_per_channel):
                    if stop_event and stop_event.is_set():
                        return
                    
                    if send(wh['url'], content, name, avatar):
                        with lock:
                            sent[0] += 1
                            if sent[0] % 10 == 0:
                                progress.update(spam_task, advance=10, description=f"[magenta]Sent: {sent[0]} | Target: {len(target_channels)*amount_per_channel}")
                            else:
                                progress.update(spam_task, advance=1)
                    else:
                         progress.update(spam_task, advance=1)
                    
                    if stop_event.wait(0.03):
                        return
                
                webhook_queue.task_done()
        
        def create_worker():
            for channel in target_channels:
                if stop_event and stop_event.is_set():
                    break
                
                channel_id = channel.get('id')
                channel_name = channel.get('name', 'unknown')
                
                webhook_url = get_or_create_webhook(token, channel_id, channel_name, name)
                if webhook_url:
                    with lock:
                        created_count[0] += 1
                        progress.update(create_task, advance=1, description=f"[cyan]Created: {created_count[0]} | Failed: {failed_create[0]}")
                    
                    webhook_queue.put({
                        'url': webhook_url,
                        'channel_name': channel_name
                    })
                else:
                    with lock:
                        failed_create[0] += 1
                        progress.update(create_task, advance=1, description=f"[red]Failed: {failed_create[0]}")
                
                if stop_event.wait(0.05):
                    break
            
            done_creating[0] = True
        
        producer = threading.Thread(target=create_worker, daemon=True)
        producer.start()
        
        spam_threads = min(thread_count, 20)
        consumers = []
        for _ in range(spam_threads):
            t = threading.Thread(target=spam_worker, daemon=True)
            t.start()
            consumers.append(t)
        
        # Wait for producer
        while producer.is_alive():
            if stop_event.is_set():
                return 0
            time.sleep(0.1)
        
        # Wait for consumers
        while any(t.is_alive() for t in consumers):
            if stop_event.is_set():
                return 0
            time.sleep(0.1)
    
    ui.print_success(f"Finished! Created {created_count[0]} webhooks, Sent {sent[0]} messages")
    return sent[0]
