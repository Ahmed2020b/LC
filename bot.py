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
        print(f"Attempting to connect to database...") # Simplified print
        
        if conn is not None:
            try:
                conn.close()
                # print("Closed existing database connection") # Removed print
            except Exception as close_err:
                print(f"Error closing existing database connection: {close_err}")
                pass
        
        # Add connection timeout and retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                # print(f"Attempt {retry_count + 1} to connect to database...") # Removed print
                # Connect using the connection string
                conn = sqlitecloud.connect(connection_string)
                # print("Connection object created") # Removed print
                
                cursor = conn.cursor()
                # print("Cursor created") # Removed print
                
                # Test the connection with a simple query
                # print("Testing connection with SELECT 1...") # Removed print
                cursor.execute('SELECT 1')
                # result = cursor.fetchone()
                # print(f"Test query result: {result}") # Removed print
                
                # Create auto-responder table if it doesn't exist
                # print("Creating auto_responses table if it doesn't exist...") # Removed print
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auto_responses (
                        guild_id TEXT,
                        trigger TEXT,
                        response TEXT,
                        PRIMARY KEY (guild_id, trigger)
                    )
                ''')
                # print("Table creation query executed") # Removed print
                
                # print("Attempting to commit table creation...") # Removed print
                conn.commit()
                # print("Table creation committed") # Removed print
                
                print("Successfully connected to the database!")
                return True
            except Exception as e:
                retry_count += 1
                print(f"Database connection attempt failed: {str(e)}") # Simplified print
                # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
                if retry_count < max_retries:
                    print(f"Retrying in 5 seconds... (Attempt {retry_count + 1} of {max_retries})")
                    time.sleep(5)
                else:
                    print("Max retries reached. Could not connect to database.")
                    return False
                    
    except Exception as e:
        print(f"Error initializing database: {str(e)}") # Simplified print
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
        print("Please check your SQLiteCloud environment variables (API_KEY, DB, HOST, PORT)")
        return False

def ensure_db_connection():
    global conn, cursor
    try:
        if conn is None or cursor is None:
            # print("Database connection or cursor is None. Re-initializing...") # Removed print
            return initialize_database()
            
        if not conn.is_connected():
            # print("Database connection is not active. Re-initializing...") # Removed print
            return initialize_database()
            
        # Test the connection
        # print("Testing existing database connection...") # Removed print
        cursor.execute('SELECT 1')
        # result = cursor.fetchone()
        # print(f"Connection test result: {result}") # Removed print
        
        # print("Database connection is active and working.") # Removed print
        return True
    except Exception as e:
        print(f"Error in ensure_db_connection: {str(e)}") # Simplified print
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
        # print("Attempting to re-initialize database connection...") # Removed print
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
    # print(f"Message received: {message.content} from {message.author}") # Removed detailed print
    if message.author.bot:
        # print("Ignoring bot message") # Removed print
        return

    # print("Message is not from a bot.") # Removed print
    # Check for auto-responses
    try:
        # Ensure database connection before query
        # print("Checking database connection...") # Removed print
        if not ensure_db_connection():
            # print("Database connection check failed") # Removed print
            return
            
        # print("Database connection verified, preparing to query...") # Removed print
        # print(f"Conn ID: {id(conn)}, Cursor ID: {id(cursor)}") # Removed Debug IDs
        
        # Add a small delay before querying as a debugging step
        # await asyncio.sleep(0.1) # Removed sleep unless necessary for specific db issues
        # print("Delayed before query.") # Removed print

        current_guild_id = str(message.guild.id)
        trigger_lower = message.content.lower()
        print(f"Checking database for trigger: {trigger_lower} in guild: {current_guild_id}") # Added back print
        
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                      (current_guild_id, trigger_lower))
        result = cursor.fetchone()
        
        # Debug: If no result found, try querying again once immediately (simplified debug)
        if not result:
            print("Debug: Query returned no result, trying one more time...") # Added back print
            # Ensure connection is still active before re-querying
            if ensure_db_connection():
                 cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                               (current_guild_id, trigger_lower))
                 result = cursor.fetchone()
                 if result:
                     print("Debug: Re-query successful.") # Added back print
                 else:
                     print("Debug: Re-query also returned no result.") # Added back print
            # else:
                 # print("Debug: Failed to re-ensure connection for re-query.") # Removed print

        if result:
            # print(f"Found auto-response: trigger='{result[0]}', response='{result[1]}'") # Removed detailed print
            await message.reply(result[1])
            # print("Sent auto-response.") # Removed print
        else:
            print(f"No auto-response found for this trigger: {trigger_lower}") # Added back print
            # Debug: List all triggers for this guild if none found (simplified debug)
            # try:
                # Ensure database connection before debug query
                # if not ensure_db_connection():
                    # print("Failed to ensure database connection before debug listing.")
                    # Continue without listing if connection fails
                # else:
                    # print("Debug: Executing SELECT for all triggers...")
                    # Add a small delay before debug query
                    # await asyncio.sleep(0.1)
                    # print("Debug: Delayed before debug query.")
                    # cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?', (current_guild_id,))
                    # all_responses = cursor.fetchall()
                    # print(f"All triggers found for guild {current_guild_id}:")
                    # if all_responses:
                        # for trg, rsp in all_responses:
                            # print(f"  - Trigger: '{trg}', Response: '{rsp}'")
                    # else:
                        # print("  (No auto-responses found for this guild at all)")
            # except Exception as list_err:
                # print(f"Error listing triggers for debug: {list_err}")

    except Exception as e:
        print(f"Error in auto-response processing: {e}")
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging


    # IMPORTANT: This line is crucial to allow other commands to work
    await bot.process_commands(message)
    # print("Processed commands.") # Removed print

@bot.tree.command(name="addresponse", description="Add an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def addresponse(interaction: discord.Interaction, trigger: str, response: str):
    """Add an auto-response trigger."""
    # print(f"Attempting to add auto-response: trigger='{trigger}', response='{response}' for guild={interaction.guild_id}") # Removed detailed print
    try:
        # Ensure database connection before insert
        # print("Checking database connection...") # Removed print
        if not ensure_db_connection():
            # print("Database connection check failed") # Removed print
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return
                
        # print("Database connection verified, preparing to insert...") # Removed print
        try:
            # print(f"Executing INSERT OR REPLACE with values: guild_id={str(interaction.guild_id)}, trigger={trigger.lower()}, response={response}") # Removed detailed print
            cursor.execute('INSERT OR REPLACE INTO auto_responses (guild_id, trigger, response) VALUES (?, ?, ?)',
                          (str(interaction.guild_id), trigger.lower(), response))
            # print("INSERT OR REPLACE executed successfully") # Removed print
        except Exception as db_error:
            print(f"Database insert error: {db_error}") # Simplified print
            # print(f"Error type: {type(db_error).__name__}") # Kept error type for debugging
            await interaction.response.send_message("حدث خطأ أثناء حفظ الرد في قاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return
        
        # print("Attempting to commit changes...") # Removed print
        try:
            # Ensure database connection before commit
            # print("Verifying database connection before commit...") # Removed print
            if not ensure_db_connection():
                # print("Database connection verification failed before commit") # Removed print
                await interaction.response.send_message("فشل الاتصال بقاعدة البيانات أثناء حفظ الرد. يرجى المحاولة مرة أخرى.")
                return
                
            # print("Executing commit...") # Removed print
            conn.commit()
            # print("Changes committed successfully") # Removed print
        except Exception as commit_error:
            print(f"Database commit error: {commit_error}") # Simplified print
            # print(f"Error type: {type(commit_error).__name__}") # Kept error type for debugging
            await interaction.response.send_message("حدث خطأ أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
            return
        
        # print("Sending success message to user...") # Removed print
        await interaction.response.send_message(f'تم إضافة الرد التلقائي: عندما يكتب أحد "{trigger}" سيرد البوت "{response}"')
        # print("Success message sent") # Removed print
    except Exception as e:
        print(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
        await interaction.response.send_message(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        # print("Error message sent to user") # Removed print

@bot.tree.command(name="removeresponse", description="Remove an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def removeresponse(interaction: discord.Interaction, trigger: str):
    """Remove an auto-response trigger."""
    # print(f"Attempting to remove auto-response: trigger='{trigger}' for guild={interaction.guild_id}") # Removed detailed print
    try:
        # Ensure database connection before delete
        # print("Checking database connection...") # Removed print
        if not ensure_db_connection():
            # print("Database connection check failed") # Removed print
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return

        # print("Database connection verified, preparing to delete...") # Removed print
        try:
            # print("Executing DELETE...") # Removed print
            cursor.execute('DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?',
                          (str(interaction.guild_id), trigger.lower()))
            # print("DELETE executed.") # Removed print
        except Exception as db_error:
            print(f"Database delete error: {db_error}") # Simplified print
            # print(f"Error type: {type(db_error).__name__}") # Kept error type for debugging
            await interaction.response.send_message("حدث خطأ أثناء حذف الرد من قاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return

        # print("Attempting to commit changes...") # Removed print
        try:
            # Ensure database connection before commit
            # print("Verifying database connection before commit...") # Removed print
            if not ensure_db_connection():
                # print("Database connection verification failed before commit") # Removed print
                await interaction.response.send_message("فشل الاتصال بقاعدة البيانات أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
                return
                
            # print("Executing commit...") # Removed print
            conn.commit()
            # print("Changes committed.") # Removed print
        except Exception as commit_error:
            print(f"Database commit error: {commit_error}") # Simplified print
            # print(f"Error type: {type(commit_error).__name__}") # Kept error type for debugging
            await interaction.response.send_message("حدث خطأ أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
            return

        if cursor.rowcount > 0:
            await interaction.response.send_message(f'تم حذف الرد التلقائي "{trigger}"')
            # print("Sent confirmation message for removal.") # Removed print
        else:
            await interaction.response.send_message(f'لم يتم العثور على رد تلقائي بهذا المحفز "{trigger}"')
            # print("Sent not found message for removal.") # Removed print
    except Exception as e:
        print(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
        await interaction.response.send_message(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        # print("Sent error message for removal.") # Removed print

@bot.tree.command(name="listresponses", description="List all auto-response triggers")
@app_commands.checks.has_permissions(manage_guild=True)
async def listresponses(interaction: discord.Interaction):
    """List all auto-response triggers."""
    # print(f"Attempting to list auto-responses for guild={interaction.guild_id} (from listresponses command)") # Removed detailed print
    try:
        # Ensure database connection before query
        # print("Checking database connection...") # Removed print
        if not ensure_db_connection():
            # print("Database connection check failed") # Removed print
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return
                    
        # print(f"Conn ID: {id(conn)}, Cursor ID: {id(cursor)}") # Removed Debug IDs
        
        # Add a small delay before querying as a debugging step
        # await asyncio.sleep(0.1) # Removed sleep
        # print("Delayed before query in listresponses.") # Removed print

        # print("Executing SELECT in listresponses command...") # Removed print
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?',
                      (str(interaction.guild_id),))
        responses = cursor.fetchall()
        # print("Executed SELECT in listresponses command.") # Removed print

        # Debug: Print the raw result from the listresponses command
        # print(f"listresponses command Result: {responses}") 
            
        if responses:
            response_list = '\n'.join([f'• "{trigger}" → "{response}"' for trigger, response in responses])
            await interaction.response.send_message(f'**قائمة الردود التلقائية:**\n{response_list}')
            # print("Sent list of responses from listresponses command.") # Removed print
        else:
            await interaction.response.send_message('لا توجد ردود تلقائية مضافة.')
            # print("Sent message indicating no responses found from listresponses command.") # Removed print
    except Exception as e:
        print(f'حدث خطأ أثناء عرض الردود التلقائية: {e}') # Simplified print
        # print(f"Error type: {type(e).__name__}") # Kept error type for debugging
        await interaction.response.send_message(f'حدث خطأ أثناء عرض الردود التلقائية: {e}')
        # print("Sent error message for listing from listresponses command.") # Removed print

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