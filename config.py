"""
Configuration - Cross-platform settings management
Production-ready with PyInstaller support
"""

import os
import sys
import json
import threading
from pathlib import Path

# Global stop event for Ctrl+C handling
stop_event = threading.Event()
# Global event for Bot Kicked detection
kicked_event = threading.Event()

# Initialize colorama for Windows ANSI color support
try:
    import colorama
    colorama.init(autoreset=False)
except ImportError:
    pass  # colorama optional, colors may not work on Windows without it


def get_frozen() -> bool:
    """Check if running as PyInstaller frozen executable"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> Path:
    """Get base path - handles PyInstaller frozen state"""
    if get_frozen():
        # Running as compiled exe - use exe directory
        return Path(sys.executable).parent
    else:
        # Running as script - use script directory
        return Path(__file__).parent


def get_resource_path(relative_path: str) -> Path:
    """Get path to bundled resource (for PyInstaller)"""
    if get_frozen():
        # PyInstaller stores bundled files in _MEIPASS
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative_path


def get_app_data_dir() -> Path:
    """
    Get cross-platform app data directory for settings storage.
    Returns directory in user's app data location.
    """
    app_name = "ExistNuker"
    
    if sys.platform == 'win32':
        # Windows: %APPDATA%/DiscordNuker
        base = Path(os.environ.get('APPDATA', Path.home()))
    elif sys.platform == 'darwin':
        # macOS: ~/Library/Application Support/DiscordNuker
        base = Path.home() / 'Library' / 'Application Support'
    else:
        # Linux/other: ~/.config/DiscordNuker
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    
    app_dir = base / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


# Settings file - stored in app data directory OR alongside exe
def get_settings_path() -> Path:
    """Get path to settings file (portable mode: alongside exe, otherwise app data)"""
    # Check for portable mode (settings.json next to exe/script)
    local_settings = get_base_path() / "settings.json"
    if local_settings.exists():
        return local_settings
    
    # For frozen exe, prefer portable mode (create next to exe)
    if get_frozen():
        return local_settings
    
    # For development, use local directory
    return get_base_path() / "settings.json"


# Settings file path
SETTINGS_FILE = get_settings_path()

# Default settings
DEFAULT_SETTINGS = {
    "token": None,
    "webhook_name": "ExistNuker",
    "webhook_avatar": "https://i.pinimg.com/originals/a5/4b/a2/a54ba238b3d4843e0dcd3294d168fbca.gif",
    "threads": 40,
    "timeout": 10000
}

# Current settings (loaded at runtime)
SETTINGS = {}


def load_settings():
    """Load settings from JSON file"""
    global SETTINGS
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                SETTINGS = json.load(f)
                # Fill in missing defaults
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in SETTINGS:
                        SETTINGS[key] = value
        else:
            SETTINGS = DEFAULT_SETTINGS.copy()
    except Exception:
        SETTINGS = DEFAULT_SETTINGS.copy()
    return SETTINGS


def save_settings():
    """Save current settings to JSON file"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SETTINGS, f, indent=2)
        return True
    except Exception:
        return False


def get_setting(key, default=None):
    """Get a setting value"""
    if not SETTINGS:
        load_settings()
    return SETTINGS.get(key, default)


def set_setting(key, value):
    """Set a setting value and save"""
    global SETTINGS
    if not SETTINGS:
        load_settings()
    SETTINGS[key] = value
    save_settings()


def get_token():
    """Get saved token"""
    return get_setting("token")


def save_token(token):
    """Save token to settings"""
    set_setting("token", token)


def delete_token():
    """Clear saved token"""
    set_setting("token", None)


def get_webhook_name():
    """Get webhook name"""
    return get_setting("webhook_name", DEFAULT_SETTINGS["webhook_name"])


def set_webhook_name(name):
    """Set webhook name"""
    set_setting("webhook_name", name)


def get_webhook_avatar():
    """Get webhook avatar URL"""
    return get_setting("webhook_avatar", DEFAULT_SETTINGS["webhook_avatar"])


def set_webhook_avatar(url):
    """Set webhook avatar URL"""
    set_setting("webhook_avatar", url)


# Initialize settings on import
load_settings()


# Runtime variables (not saved)
TOKEN = get_token()
GUILD_ID = None
THREADS = get_setting("threads", 40)
TIMEOUT = get_setting("timeout", 10000)


# Console colors - ANSI escape codes (cross-platform with colorama)
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    
    # Disable colors if running in non-interactive mode or redirected
    @classmethod
    def disable(cls):
        """Disable all colors"""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.MAGENTA = ""
        cls.CYAN = ""
        cls.WHITE = ""
        cls.RESET = ""


# Check if stdout supports colors
def _supports_color():
    """Check if the terminal supports colors"""
    if not hasattr(sys.stdout, 'isatty'):
        return False
    if not sys.stdout.isatty():
        return False
    if sys.platform == 'win32':
        # Windows 10+ supports ANSI, older versions need colorama
        return True
    return True


if not _supports_color():
    Colors.disable()


# Application logo
LOGO = r"""
    ______      _      __  _   __      __             
   / ____/  __ (_)____/ /_/ | / /_  __/ /_____  _____ 
  / __/ | |/_// / ___/ __/  |/ / / / / //_/ _ \/ ___/ 
 / /____>  < / (__  ) /_/ /|  / /_/ / ,< /  __/ /     
/_____/_/|_|/_/____/\__/_/ |_/\__,_/_/|_|\___/_/      

    ExistNuker - https://github.com/myexistences/ExistNuker
"""
