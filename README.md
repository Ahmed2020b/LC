# Discord Auto-Response Bot

A Discord bot that provides auto-response functionality and moderation commands. The bot uses SQLiteCloud for database storage and supports multiple guilds.

## Features

- Auto-response system with customizable triggers and responses
- Moderation commands (kick, ban, unban, mute, unmute)
- Message clearing
- Multi-guild support
- Persistent storage using SQLiteCloud

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd discord-auto-response-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token
SQLITECLOUD_API_KEY=your_sqlitecloud_api_key
SQLITECLOUD_DB=your_database_name
SQLITECLOUD_HOST=your_host
SQLITECLOUD_PORT=your_port
```

4. Run the bot:
```bash
python bot.py
```

## Commands

### Auto-Response Commands
- `/addresponse trigger:<text> response:<text>` - Add a new auto-response
- `/removeresponse trigger:<text>` - Remove an auto-response
- `/listresponses` - List all auto-responses in the server

### Moderation Commands
- `/kick @member [reason]` - Kick a member from the server
- `/ban @member [reason]` - Ban a member from the server
- `/unban username#discriminator` - Unban a user
- `/mute @member` - Mute a member
- `/unmute @member` - Unmute a member
- `/clear [amount]` - Clear messages (default: 5)

## Requirements

- Python 3.8 or higher
- discord.py
- python-dotenv
- sqlitecloud

## License

MIT License 