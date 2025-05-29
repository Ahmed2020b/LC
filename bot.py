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
                
                # Create auto-responder table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auto_responses (
                        guild_id TEXT,
                        trigger TEXT,
                        response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (guild_id, trigger)
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_guild_trigger ON auto_responses(guild_id, trigger)')
                
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

    try:
        # Ensure database connection before query attempt
        if not ensure_db_connection():
            print("on_message: Initial database connection check failed.")
            # Attempt to send an error message to the channel if possible
            try:
                await message.channel.send("❌ Error: Cannot connect to the database for auto-responses.")
            except:
                pass # Ignore if sending message fails
            return

        current_guild_id = str(message.guild.id)
        trigger_lower = message.content.lower()
        print(f"on_message: Processing message from guild {current_guild_id} with content '{trigger_lower}'")

        try:
            # Attempt to query the database
            print(f"on_message: Attempting database query for trigger '{trigger_lower}'...")
            cursor.execute('SELECT response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                          (current_guild_id, trigger_lower))
            print("on_message: Query executed.")

            result = cursor.fetchone()
            print(f"on_message: Fetched result: {result}")

            if result:
                response = result[0]
                print(f"on_message: Found auto-response: {response}. Replying...")
                await message.reply(response)
                print("on_message: Reply sent.")
            else:
                print(f"on_message: No auto-response found for trigger '{trigger_lower}'.")

        except Exception as db_error:
            # Catch specific database errors and try to reinitialize
            print(f"on_message: Database error during query/fetch: {db_error}")
            print("on_message: Attempting to reinitialize database connection due to error...")
            if initialize_database():
                print("on_message: Database reinitialized successfully after error.")
                # Note: We don't retry the message here to avoid potential duplicates,
                # but the connection should be ready for the next message.
            else:
                 print("on_message: Failed to reinitialize database after error.")
                 try:
                     await message.channel.send("❌ Error: Database connection lost. Auto-responses may not work.")
                 except:
                     pass # Ignore if sending message fails

    except Exception as e:
        print(f"on_message: General error in auto-response processing: {e}")
        # Attempt to send an error message to the channel if possible
        try:
            await message.channel.send("❌ An unexpected error occurred while processing auto-responses.")
        except:
            pass # Ignore if sending message fails

    # IMPORTANT: This line is crucial to allow other commands to work
    await bot.process_commands(message)

@bot.tree.command(name="addresponse", description="Add an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def addresponse(interaction: discord.Interaction, trigger: str, response: str):
    """Add an auto-response trigger."""
    guild_id = str(interaction.guild_id)
    trigger_lower = trigger.lower()
    print(f"addresponse: Attempting to add response for guild {guild_id}, trigger '{trigger_lower}', response '{response}'")

    try:
        print("addresponse: Checking database connection...")
        if not ensure_db_connection():
            print("addresponse: Database connection check failed.")
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        print("addresponse: Connection ensured. Preparing to execute INSERT OR REPLACE.")
        try:
            cursor.execute('INSERT OR REPLACE INTO auto_responses (guild_id, trigger, response) VALUES (?, ?, ?)',
                          (guild_id, trigger_lower, response))
            print("addresponse: INSERT OR REPLACE executed.")
        except Exception as db_execute_error:
            print(f"addresponse: Database execute error: {db_execute_error}")
            await interaction.response.send_message("حدث خطأ أثناء حفظ الرد في قاعدة البيانات (تنفيذ). يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        print("addresponse: Preparing to commit changes.")
        try:
            conn.commit()
            print("addresponse: Changes committed.")
        except Exception as db_commit_error:
            print(f"addresponse: Database commit error: {db_commit_error}")
            await interaction.response.send_message("حدث خطأ أثناء حفظ التغييرات (كوميت). يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        print("addresponse: Successfully added/updated response. Sending confirmation.")
        await interaction.response.send_message(f'تم إضافة الرد التلقائي: عندما يكتب أحد "{trigger}" سيرد البوت "{response}"')
        print("addresponse: Confirmation message sent.")

    except Exception as e:
        print(f'addresponse: An unexpected error occurred: {e}')
        await interaction.response.send_message(f'حدث خطأ غير متوقع أثناء إضافة الرد التلقائي: {e}', ephemeral=True)

@bot.tree.command(name="removeresponse", description="Remove an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def removeresponse(interaction: discord.Interaction, trigger: str):
    """Remove an auto-response trigger."""
    try:
        if not ensure_db_connection():
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return

        cursor.execute('DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?',
                      (str(interaction.guild_id), trigger.lower()))
    except Exception as db_error:
        print(f"Database delete error: {db_error}")
        await interaction.response.send_message("حدث خطأ أثناء حذف الرد من قاعدة البيانات. يرجى المحاولة مرة أخرى.")
        return

    try:
        conn.commit()
    except Exception as commit_error:
        print(f"Database commit error: {commit_error}")
        await interaction.response.send_message("حدث خطأ أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
        return

    if cursor.rowcount > 0:
        await interaction.response.send_message(f'تم حذف الرد التلقائي "{trigger}"')
    else:
        await interaction.response.send_message(f'لم يتم العثور على رد تلقائي بهذا المحفز "{trigger}"')

@bot.tree.command(name="listresponses", description="List all auto-response triggers")
@app_commands.checks.has_permissions(manage_guild=True)
async def listresponses(interaction: discord.Interaction):
    """List all auto-response triggers."""
    guild_id = str(interaction.guild_id)
    print(f"listresponses: Attempting to list responses for guild {guild_id}")

    try:
        print("listresponses: Checking database connection...")
        if not ensure_db_connection():
            print("listresponses: Database connection check failed.")
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        print("listresponses: Connection ensured. Preparing to execute SELECT.")
        try:
            cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?',
                          (guild_id,))
            print("listresponses: SELECT executed.")

            responses = cursor.fetchall()
            print(f"listresponses: Fetched results: {responses}")

        except Exception as db_execute_error:
            print(f"listresponses: Database execute error: {db_execute_error}")
            await interaction.response.send_message("حدث خطأ أثناء عرض الردود التلقائية (تنفيذ). يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        if responses:
            response_list = '\n'.join([f'• "{trigger}" → "{response}"' for trigger, response in responses])
            print(f"listresponses: Found {len(responses)} responses. Sending list.")
            await interaction.response.send_message(f'**قائمة الردود التلقائية:**\n{response_list}')
            print("listresponses: List sent.")
        else:
            print("listresponses: No responses found.")
            await interaction.response.send_message('لا توجد ردود تلقائية مضافة.')
            print("listresponses: No responses message sent.")

    except Exception as e:
        print(f'listresponses: An unexpected error occurred: {e}')
        await interaction.response.send_message(f'حدث خطأ غير متوقع أثناء عرض الردود التلقائية: {e}', ephemeral=True)

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