import os
# print("os imported")

print("Bot script started!")
import discord
# print("discord imported")
from discord.ext import commands
# print("commands imported")
from discord import app_commands
# print("app_commands imported")
from dotenv import load_dotenv
import sqlitecloud
import time
import asyncio # Import asyncio for sleep
# print("dotenv imported")
# print("sqlitecloud and time imported")
# print("asyncio imported")

# Last deployment: 2024-03-19

# Load environment variables
load_dotenv()
# print(".env loaded")

# Debug environment variables
# print("Checking environment variables...")
# print(f"Current working directory: {os.getcwd()}")

# Global database variables
conn = None
cursor = None

def initialize_database():
    global conn, cursor
    try:
        # Get database connection details from environment variables
        api_key = os.getenv('SQLITECLOUD_API_KEY')
        db_name = os.getenv('SQLITECLOUD_DB')
        host = os.getenv('SQLITECLOUD_HOST')
        port = os.getenv('SQLITECLOUD_PORT')

        # Validate environment variables
        if not api_key:
            print("Error: SQLITECLOUD_API_KEY environment variable is not set")
            return False
        if not db_name:
            print("Error: SQLITECLOUD_DB environment variable is not set")
            return False
        if not host:
            print("Error: SQLITECLOUD_HOST environment variable is not set")
            return False
        if not port:
            print("Error: SQLITECLOUD_PORT environment variable is not set")
            return False
            
        # Construct the connection string
        connection_string = f"sqlitecloud://{host}:{port}/{db_name}?apikey={api_key}"
        print(f"Attempting to connect to database...")
        
        if conn is not None:
            try:
                conn.close()
            except Exception as close_err:
                print(f"Error closing existing database connection: {close_err}")
                pass
        
        # Add connection timeout and retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                conn = sqlitecloud.connect(connection_string)
                cursor = conn.cursor()
                
                # Test the connection with a simple query
                cursor.execute('SELECT 1')
                
                # Note: Auto-response table creation is removed here.
                
                conn.commit()
                print("Successfully connected to the database!")
                return True
            except Exception as e:
                retry_count += 1
                print(f"Database connection attempt failed: {str(e)}")
                if retry_count < max_retries:
                    print(f"Retrying in 5 seconds... (Attempt {retry_count + 1} of {max_retries})")
                    time.sleep(5)
                else:
                    print("Max retries reached. Could not connect to database.")
                    return False
                    
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        print("Please check your SQLiteCloud environment variables (API_KEY, DB, HOST, PORT)")
        return False

def ensure_db_connection():
    global conn, cursor
    try:
        if conn is None or cursor is None:
            return initialize_database()
            
        try:
            # Test the connection with a simple query
            cursor.execute('SELECT 1')
            return True
        except Exception:
            # If the test fails, try to reinitialize
            return initialize_database()
            
    except Exception as e:
        print(f"Error in ensure_db_connection: {str(e)}")
        return initialize_database()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='-', intents=intents) # Prefix is not used for slash commands, but required for Bot class
        
    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced.") # Added confirmation print
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        # Initialize database when bot starts
        if not initialize_database():
            print("Failed to connect to database on startup. Database functionality will not work.")

bot = Bot()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # IMPORTANT: This line is crucial to allow other commands to work
    await bot.process_commands(message)

# Removed auto-response commands (addresponse, removeresponse, listresponses)

# Add moderation commands (keeping these as they are not related to auto-responses)
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Kick a member from the server."""
    await member.kick(reason=reason)
    await interaction.response.send_message(f'{member.mention} تم طرده بنجاح!')

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Ban a member from the server."""
    await member.ban(reason=reason)
    await interaction.response.send_message(f'{member.mention} تم حظره بنجاح!')

@bot.tree.command(name="unban", description="Unban a user by name#discriminator")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user: str):
    """Unban a user by name#discriminator."""
    banned_users = await interaction.guild.bans()
    name, discriminator = user.split('#')
    for ban_entry in banned_users:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (name, discriminator):
            await interaction.guild.unban(ban_entry.user)
            await interaction.response.send_message(f'{ban_entry.user.mention} تم فك الحظر عنه!')
            return
    await interaction.response.send_message('المستخدم غير موجود في قائمة المحظورين.')

@bot.tree.command(name="mute", description="Mute a member by adding a Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member):
    """Mute a member by adding a Muted role."""
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await interaction.guild.create_role(name="Muted")
        for channel in interaction.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False, read_message_history=True, read_messages=True)
    await member.add_roles(muted_role)
    await interaction.response.send_message(f'{member.mention} تم إعطاؤه ميوت!')

@bot.tree.command(name="unmute", description="Unmute a member by removing the Muted role")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    """Unmute a member by removing the Muted role."""
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await interaction.response.send_message(f'{member.mention} تم فك الميوت عنه!')
    else:
        await interaction.response.send_message('المستخدم ليس عليه ميوت.')

@bot.tree.command(name="clear", description="Clear a number of messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int = 5):
    """Clear a number of messages (default 5)."""
    await interaction.channel.purge(limit=amount+1)
    await interaction.response.send_message(f'تم حذف {amount} رسالة!', delete_after=3)

bot.run(os.getenv('DISCORD_TOKEN')) 