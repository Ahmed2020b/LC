# Discord Bot

A simple Discord bot built with discord.py that responds to basic commands.

## Features

- `!hello` - Bot responds with a friendly greeting
- `!ping` - Check the bot's latency

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Getting a Discord Bot Token

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Copy the token and add it to your `.env` file
5. Enable the "Message Content Intent" under the Bot section
6. Use the OAuth2 URL Generator to create an invite link for your bot

## Commands

- `!hello` - Get a friendly greeting from the bot
- `!ping` - Check the bot's latency 