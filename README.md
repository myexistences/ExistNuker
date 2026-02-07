<div align="center">

# ⚡ ExistNuker ⚡
### Advanced Discord Server Management & Moderation Tool

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<img src="https://via.placeholder.com/800x400?text=ExistNuker+Dashboard" alt="ExistNuker Dashboard" width="800"/>

<br/>

**ExistNuker** is a powerful, multi-threaded Discord server management tool featuring a beautiful, unresponsive terminal interface. Built with performance and user experience in mind, it allows for efficient server administration through a modern CLI.

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Disclaimer](#-disclaimer)

</div>

---

## ✨ Features

### 🎨 Modern Interface
- **Rich UI**: Powered by `textual` and `rich` for a stunning visual experience.
- **Live Statistics**: Real-time progress bars showing Success/Fail/Skip counts for all operations.
- **Responsive**: Automatically adapts to terminal resizing without breaking layout.

### ⚡ High Performance
- **Multi-Threaded**: Executes operations concurrently for maximum speed.
- **Smart Rate-Limiting**: Automatically handles Discord API rate limits (429s) with retry logic.
- **Connection Pooling**: Reuses network connections to reduce latency.

### 🛡️ Smart Defense & Reliability
- **Kick Detection**: Zero-cost monitoring instantly stops operations if the bot is kicked.
- **Smart Pagination**: Intelligent member fetching that never gets stuck, even with unbannable admins.
- **Auto-Retry**: "Fast but not Reckless" mode retries failed requests once to handle network blips.
- **Instant Stop**: Press `Ctrl+C` to immediately halt all threads and return to the menu.

### 🛠️ Core Capabilities
| Feature | Description |
|---|---|
| **🚫 Mass Ban** | Fetch members and ban them with live status tracking. Supports "Fast Mode", Bot filtering, and Smart Pagination. |
| **📢 Webhook Spam** | Create webhooks and spam messages across all channels simultaneously. Includes separate Customization Menu. |
| **💬 Channel Nuke** | Bulk delete and create channels with custom names and types. |
| **🎭 Role Nuke** | Bulk delete and create roles, respecting hierarchy and managed roles. |
| **🧹 Pruning** | Kick inactive members based on inactivity period. |
| **🔒 Security** | Token input is masked with asterisks (`*`) for privacy. |

---

## 🚀 Installation

### Prerequisites
- [Python 3.12+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

### Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/myexistences/ExistNuker.git
   cd ExistNuker
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage

### Running the Tool
Simply run the main script:
```bash
python main.py
```

### Configuration
On the first launch, a `settings.json` file will be created. You can configure:
- **Token**: Your Discord Bot Token.
- **Threads**: Number of concurrent threads (recommended: 50-100).
- **Webhooks**: Default names and avatars for webhook operations.

### ⚠️ Safety Mode
Press `Ctrl+C` at data any time to instantly stop all running operations and return to the main menu.

---

## 📝 Disclaimer

> [!WARNING]
> **EDUCATIONAL PURPOSE ONLY**
> 
> This software is developed purely for educational purposes to demonstrate API interaction, multi-threading, and Python application design. 
> 
> **The developers assume no liability for misuse.** Users are responsible for complying with Discord's [Terms of Service](https://discord.com/terms) and [Community Guidelines](https://discord.com/guidelines). Do not use this tool on servers you do not own or have explicit permission to manage.

---

<div align="center">

*Created with ❤️ by [Exist](https://github.com/myexistences)*

</div>
