# Overview

This is a Discord bot built with Python that monitors manga releases from Crimson Scans website and provides automated notifications to Discord servers. The bot scrapes the website for new manga chapters and sends notifications to configured channels when new releases are detected. It also includes a role management system where users can assign themselves roles by reacting to messages with specific emojis.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- Built using discord.py library with command extensions
- Uses both slash commands (app_commands) and traditional prefix commands (!setup, !check)
- Implements a task-based system for periodic monitoring of manga releases
- Configurable per-guild settings for channel assignments and role management

## Data Storage
- JSON-based file storage system for persistence
- Three main data files:
  - `known_releases.json`: Tracks previously detected manga releases
  - `role_message.json`: Stores role assignment message configurations per guild
  - `guild_config.json`: Contains per-server channel configurations
- No database required - all data stored in local JSON files

## Web Scraping
- Uses requests library for HTTP requests to Crimson Scans website
- BeautifulSoup for HTML parsing to extract manga release information
- Monitors BASE_URL (https://crimsonscans.site/) for new content

## Role Management System
- Emoji-based role assignment using Discord reactions
- Pre-defined emoji list (1️⃣ through 🔟) for consistent role mapping
- Per-guild role message tracking with persistent storage

## Command Structure
- Hybrid command system supporting both slash commands and prefix commands
- Guild-specific configuration commands for setup
- Administrative commands for bot management and testing

## Discord Permissions
- Minimal required intents: guilds, guild_messages
- Optional intents: message_content (for prefix commands), members (for performance)
- Designed to work with reduced privilege requirements

# External Dependencies

## Python Libraries
- `discord.py`: Core Discord bot functionality and API interactions
- `requests`: HTTP client for web scraping operations
- `beautifulsoup4`: HTML parsing for extracting manga release data
- `asyncio`: Asynchronous programming support for Discord operations

## External Services
- **Discord API**: Primary platform for bot deployment and user interaction
- **Crimson Scans Website** (https://crimsonscans.site/): Target website for manga release monitoring
- No database services required - uses local file storage

## Runtime Environment
- Python 3.7+ required for discord.py compatibility
- File system access needed for JSON data persistence
- Network access required for web scraping and Discord API communication