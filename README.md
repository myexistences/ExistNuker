<div align="center">

# 💀 ExistNuker 💀
### Discord Server Nuker

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge)

<img src="https://i.imgur.com/v5PbF9R.png" alt="ExistNuker" width="800"/>

**ExistNuker** is a fast, multi-threaded Discord server nuker. Destroy servers with a single command.

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Disclaimer](#%EF%B8%8F-disclaimer)

</div>

---

## 💀 What Is This?

ExistNuker is a **Discord server destruction tool** that uses a bot token to:
- **Delete all channels** and create spam channels
- **Delete all roles** and create spam roles  
- **Ban all members** from the server
- **Spam messages** via webhooks across all channels
- **Prune inactive members**
- **Leave the server** when done

---

## ⚡ Features

| Feature | Description |
|---------|-------------|
| 🚫 **Mass Ban** | Kick bots & ban all members. Fast mode fires requests without waiting. |
| 💬 **Webhook Spam** | Create webhooks in every channel and spam messages simultaneously. |
| 📢 **Channel Nuke** | Delete all channels, then create spam channels. |
| 🎭 **Role Nuke** | Delete all roles, then create spam roles. |
| 🧹 **Prune Members** | Kick inactive members based on days of inactivity. |
| 🚪 **Leave Server** | Make the bot leave the server when finished. |
| ⚙️ **Customization** | Set custom webhook names, avatars, and spam messages. |
| 🔒 **Token Security** | Token input is masked with asterisks (`*`). |

### Performance
- **Multi-Threaded**: All operations run concurrently for maximum speed
- **Rate Limit Handling**: Automatically handles Discord's rate limits
- **Instant Stop**: Press `Ctrl+C` to immediately stop all operations

---

## 🚀 Installation

### Requirements
- [Python 3.12+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)

### Setup

```bash
# Clone the repository
git clone https://github.com/myexistences/ExistNuker.git
cd ExistNuker

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 Usage

### Run the Tool
```bash
python main.py
```

### Steps
1. **Enter Bot Token** - Paste your Discord bot token (masked with `*`)
2. **Select Server** - Choose a server the bot is in
3. **Choose Action** - Select what you want to do:
   - `1` Webhook Spam (All Channels)
   - `2` Create Channels
   - `3` Delete Channels
   - `4` Create Roles
   - `5` Delete Roles
   - `6` Ban Members
   - `7` Prune Inactive Members
   - `8` Customize Webhook Settings
   - `9` Leave Server

### Stop Operations
Press `Ctrl+C` at any time to stop all running operations.

---

## ⚠️ DISCLAIMER

> **⚠️ EDUCATIONAL & RESEARCH PURPOSES ONLY**
>
> This tool is created **strictly for educational and research purposes** to demonstrate:
> - Discord API interaction
> - Multi-threading in Python
> - Terminal UI design
>
> **THE DEVELOPER IS NOT RESPONSIBLE FOR ANY MISUSE OF THIS SOFTWARE.**
>
> By using this tool, you agree that:
> - You will **NOT** use this on servers you do not own
> - You will **NOT** use this for malicious purposes
> - You take **FULL RESPONSIBILITY** for your actions
> - You understand this violates [Discord's Terms of Service](https://discord.com/terms)
>
> **USE AT YOUR OWN RISK. THE DEVELOPER ASSUMES NO LIABILITY.**

---

<div align="center">

*Created by [Exist](https://github.com/myexistences)*

</div>
