#!/usr/bin/env python3
"""
ExistNuker
Modern Interface with Rich
"""

import sys
import os
import re
import signal
import threading
import time

# Ensure module imports work for both frozen and script modes
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    _base_path = os.path.dirname(sys.executable)
else:
    # Running as script
    _base_path = os.path.dirname(os.path.abspath(__file__))

if _base_path not in sys.path:
    sys.path.insert(0, _base_path)

import config
from config import save_token, get_token, delete_token, get_webhook_name, get_webhook_avatar, set_webhook_name, set_webhook_avatar, stop_event
from discord_api import test_token, get_bot_guilds, get_guild_info, leave_guild
from interface import ui
from rich.prompt import Prompt, Confirm

import channels
import roles
import users
import webhooks

def ctrl_c_handler(signum, frame):
    """Handle Ctrl+C"""
    ui.print_warning("\nCtrl+C detected! Stopping operation...")
    stop_event.set()

def setup_signal_handlers():
    """Setup signal handlers"""
    try:
        signal.signal(signal.SIGINT, ctrl_c_handler)
    except (ValueError, OSError):
        pass
    
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            HANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
            
            def console_ctrl_handler(ctrl_type):
                if ctrl_type == 0:  # CTRL_C_EVENT
                    ctrl_c_handler(None, None)
                    return True
                return False
            
            global _win_handler
            _win_handler = HANDLER_ROUTINE(console_ctrl_handler)
            kernel32.SetConsoleCtrlHandler(_win_handler, True)
        except Exception:
            pass

setup_signal_handlers()

def validate_and_load_token():
    """Load and validate token"""
    saved_token = get_token()
    
    if saved_token:
        with ui.status_spinner("Validating saved token..."):
            if test_token(saved_token):
                config.TOKEN = saved_token
                ui.print_success("Saved token is valid!")
                time.sleep(1)
                return True
            else:
                ui.print_error("Saved token is no longer valid!")
                delete_token()
                time.sleep(1)
    
    token_pattern = re.compile(r"[\w-]{24,}\.[\w-]{6}\.[\w-]{27,}")
    
    while True:
        ui.print_banner()
        token = ui.get_token()
        
        if not token:
            continue
            
        if not token_pattern.match(token):
            ui.print_error("Invalid token format!")
            time.sleep(1)
            continue
            
        with ui.status_spinner("Validating token..."):
            if test_token(token):
                config.TOKEN = token
                save_token(token)
                ui.print_success("Token valid and saved!")
                time.sleep(1)
                return True
            else:
                ui.print_error("Invalid bot token!")
                time.sleep(1)

def handle_webhook_spam():
    stop_event.clear()
    
    ui.print_info("Enter message content (Press Enter twice to finish):")
    lines = []
    while True:
        line = input()
        if not line and lines:
            break
        if not line and not lines:
            continue
        lines.append(line)
    
    content = "\n".join(lines)
    if not content:
        content = "@everyone Nuked!"
    
    amount = Prompt.ask("[bold cyan]Messages per channel[/bold cyan]", default="10")
    try:
        amount = int(amount)
    except ValueError:
        return

    current_name = get_webhook_name()
    current_avatar = get_webhook_avatar()
    
    ui.print_warning(f"Starting webhook spam as '{current_name}'... (Ctrl+C to stop)")
    webhooks.spam(config.TOKEN, config.GUILD_ID, content, amount, 
                  webhook_name=current_name, avatar_url=current_avatar, stop_event=stop_event)
    
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_customize_webhook():
    stop_event.clear()
    current_name = get_webhook_name()
    current_avatar = get_webhook_avatar()
    
    ui.print_info(f"Current Name: {current_name}")
    ui.print_info(f"Current Avatar: {current_avatar}")
    
    new_name = Prompt.ask("New Webhook Name", default=current_name)
    set_webhook_name(new_name)
    
    new_avatar = Prompt.ask("New Avatar URL", default=current_avatar)
    if new_avatar != current_avatar:
    # Validate image
        if webhooks.validate_image_url(new_avatar):
            set_webhook_avatar(new_avatar)
            ui.print_success("Avatar updated!")
        else:
            ui.print_error("Invalid image URL. Keeping previous avatar.")
    
    ui.print_SUCCESS("Webhook settings updated!")
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_create_channels():
    stop_event.clear()
    name = Prompt.ask("[bold cyan]Channel Name[/bold cyan]", default="nuked")
    amount = int(Prompt.ask("[bold cyan]Quantity[/bold cyan]", default="50"))
    ctype = Prompt.ask("[bold cyan]Type[/bold cyan]", choices=["text", "voice"], default="text")
    
    type_map = {'text': 0, 'voice': 2}
    
    ui.print_warning("Creating channels...")
    channels.spam(config.TOKEN, config.GUILD_ID, name, type_map[ctype], amount, stop_event=stop_event)
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_delete_channels():
    stop_event.clear()
    if ui.confirm_action("Delete ALL channels and categories?"):
        ui.print_warning("Nuking all channels...")
        channels.nuke(config.TOKEN, config.GUILD_ID, stop_event=stop_event)
        Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_create_roles():
    stop_event.clear()
    name = Prompt.ask("[bold cyan]Role Name[/bold cyan]", default="nuked")
    amount = int(Prompt.ask("[bold cyan]Quantity[/bold cyan]", default="50"))
    
    ui.print_warning("Creating roles...")
    roles.spam(config.TOKEN, config.GUILD_ID, name, amount, stop_event=stop_event)
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_delete_roles():
    stop_event.clear()
    if ui.confirm_action("Delete ALL roles?"):
        ui.print_warning("Nuking all roles...")
        roles.nuke(config.TOKEN, config.GUILD_ID, stop_event=stop_event)
        Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_ban_members():
    stop_event.clear()
    mode = Prompt.ask("[bold cyan]Mode[/bold cyan]", choices=["fetch", "fast"], default="fetch")
    fetch_mode = (mode == "fetch")
    
    ui.print_warning("Banning all members...")
    users.ban_all(config.TOKEN, config.GUILD_ID, fetch_mode=fetch_mode, stop_event=stop_event)
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def handle_prune_members():
    stop_event.clear()
    days = int(Prompt.ask("[bold cyan]Days of inactivity[/bold cyan]", default="7"))
    include_roles = Confirm.ask("Include members with roles?")
    
    ui.print_warning("Pruning members...")
    users.prune_members(config.TOKEN, config.GUILD_ID, days=days, include_roles=include_roles)
    Prompt.ask("\n[bold yellow]Press Enter to continue...[/bold yellow]")

def main():
    while True:
        if not config.TOKEN:
            if not validate_and_load_token():
                continue
        
        # Server Selection
        with ui.status_spinner("Fetching servers..."):
            guilds = get_bot_guilds(config.TOKEN)
            
        if not guilds:
            ui.print_error("Bot is not in any servers!")
            if ui.confirm_action("Change Token?"):
                delete_token()
                config.TOKEN = None
                continue
            sys.exit(0)
            
        selection = ui.select_server(guilds)
        
        if selection == 'REFRESH':
            continue
            
        if selection == 'CHANGE_TOKEN':
            delete_token()
            config.TOKEN = None
            continue
            
        if not selection:
            continue
            
        config.GUILD_ID = selection['id']
        
        # Server Menu Loop
        while True:
            # Refresh guild info for menu
            with ui.status_spinner("Fetching server info..."):
                info = get_guild_info(config.TOKEN, config.GUILD_ID)
                if not info:
                    info = selection # Fallback
            
            choice = ui.server_menu(info)
            
            if choice == "0":
                config.GUILD_ID = None
                break
            elif choice == "1": handle_webhook_spam()
            elif choice == "2": handle_create_channels()
            elif choice == "3": handle_delete_channels()
            elif choice == "4": handle_create_roles()
            elif choice == "5": handle_delete_roles()
            elif choice == "6": handle_ban_members()
            elif choice == "7": handle_prune_members()
            elif choice == "8": handle_customize_webhook()
            elif choice == "9":
                if ui.confirm_action("Make the bot LEAVE this server?"):
                    if leave_guild(config.TOKEN, config.GUILD_ID):
                        ui.print_success("Bot left the server!")
                        time.sleep(1)
                        config.GUILD_ID = None
                        break
                    else:
                        ui.print_error("Failed to leave server.")
            
            # Check if bot was kicked during operation
            if config.kicked_event.is_set():
                config.kicked_event.clear()
                ui.print_error("Bot was kicked from the server! Returning to selection...")
                time.sleep(2)
                config.GUILD_ID = None
                break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        ui.print_error(str(e))
        input("Press Enter to exit...")
