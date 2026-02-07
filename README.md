# ExistNuker

![Interface Screenshot](https://via.placeholder.com/800x400?text=Place+Screenshot+Here)

**ExistNuker** is a robust, Python-based Discord server management and moderation tool designed for educational purposes. It features a modern, interactive terminal interface powered by `rich`, offering a user-friendly experience for managing channels, roles, webhooks, and members.

> [!WARNING]
> **EDUCATIONAL PURPOSE ONLY**
> This tool is developed strictly for educational purposes to demonstrate API interaction, rate limit handling, and Python application structure. The developers assume no liability for misuse. Users are responsible for complying with Discord's Terms of Service.

## ✨ Features

- **Modern UI**: Beautiful terminal interface with interactive menus and progress tracking.
- **Cross-Platform**: Fully compatible with Windows, macOS, and Linux.
- **Performance**: Multi-threaded operations for maximum efficiency.
- **Resilient**: Smart rate-limit handling and automatic retries.
- **Safety**: Built-in "Safety Mode" (Ctrl+C instantly stops operations).

## 🛠️ Capabilities

- **Webhook Management**: Create and manage webhooks with custom names and avatars.
- **Channel Operations**: Bulk create or delete channels and categories.
- **Role Management**: Bulk create or delete roles.
- **Member Moderation**:
  - **Fetch Mode**: Thoroughly bans members.
  - **Fast Mode**: Rapidly bans members (optimized for speed).
  - **Pruning**: Remove inactive members.

## 🚀 Installation & Usage

### 1. Requirements

- Python 3.8+
- [Git](https://git-scm.com/)

### 2. Installation

```bash
git clone https://github.com/myexistences/ExistNuker.git
cd ExistNuker
pip install -r requirements.txt
```

### 3. Running

```bash
python main.py
```

## ⚙️ Configuration

The tool automatically creates a `settings.json` file on first run. You can configure:
- `token`: Your Bot Token
- `webhook_name`: Default webhook name
- `webhook_avatar`: Default webhook avatar URL
- `threads`: Number of concurrent threads
- `timeout`: Request timeout

## 📜 License

This project is open-source. Please use responsibly.

---
*Created by [Exist](https://github.com/myexistences)*
