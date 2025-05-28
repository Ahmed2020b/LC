import os
print("os imported")

print("Bot script started!")
import discord
print("discord imported")
from discord.ext import commands
print("commands imported")
from discord import app_commands
print("app_commands imported")
from dotenv import load_dotenv
import sqlitecloud
import time
import asyncio # Import asyncio for sleep
print("dotenv imported")
print("sqlitecloud and time imported")
print("asyncio imported")

# Last deployment: 2024-03-19

# Load environment variables
load_dotenv()
print(".env loaded")

# Debug environment variables
print("Checking environment variables...")
print(f"Current working directory: {os.getcwd()}")
# Removed printing all environment variables for brevity/security
database_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL exists: {database_url is not None}")
if database_url:
    print(f"DATABASE_URL length: {len(database_url)}")
    print(f"DATABASE_URL starts with: {database_url[:20]}...")

# Global database variables
conn = None
cursor = None

def initialize_database():
    global conn, cursor
    try:
        # Validate DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("Error: DATABASE_URL environment variable is not set")
            print("Please make sure to set DATABASE_URL in Railway's environment variables")
            return False
            
        print(f"Attempting to connect to database with URL: {database_url[:20]}...")  # Print first 20 chars for security
        
        if conn is not None:
            try:
                conn.close()
                print("Closed existing database connection")
            except Exception as close_err:
                print(f"Error closing existing database connection: {close_err}")
                pass
        
        # Add connection timeout and retry logic
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                print(f"Attempt {retry_count + 1} to connect to database...")
                conn = sqlitecloud.connect(database_url, timeout=30)  # 30 second timeout
                print("Connection object created")
                
                cursor = conn.cursor()
                print("Cursor created")
                
                # Test the connection with a simple query
                print("Testing connection with SELECT 1...")
                cursor.execute('SELECT 1')
                result = cursor.fetchone()
                print(f"Test query result: {result}")
                
                # Create auto-responder table if it doesn't exist
                print("Creating auto_responses table if it doesn't exist...")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS auto_responses (
                        guild_id TEXT,
                        trigger TEXT,
                        response TEXT,
                        PRIMARY KEY (guild_id, trigger)
                    )
                ''')
                print("Table creation query executed")
                
                print("Attempting to commit table creation...")
                conn.commit()
                print("Table creation committed")
                
                print("Successfully connected to the database!")
                return True
            except Exception as e:
                retry_count += 1
                print(f"Attempt {retry_count} failed with error: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                if retry_count < max_retries:
                    print(f"Retrying in 5 seconds... (Attempt {retry_count + 1} of {max_retries})")
                    time.sleep(5)
                else:
                    print("Max retries reached. Could not connect to database.")
                    return False
                    
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print("Please check your DATABASE_URL in Railway environment variables")
        return False

def ensure_db_connection():
    global conn, cursor
    try:
        if conn is None or cursor is None:
            print("Database connection or cursor is None. Re-initializing...")
            return initialize_database()
            
        if not conn.is_connected():
            print("Database connection is not active. Re-initializing...")
            return initialize_database()
            
        # Test the connection
        print("Testing existing database connection...")
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        print(f"Connection test result: {result}")
        
        print("Database connection is active and working.")
        return True
    except Exception as e:
        print(f"Error in ensure_db_connection: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print("Attempting to re-initialize database connection...")
        return initialize_database()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='-', intents=intents)
        
    async def setup_hook(self):
        await self.tree.sync()
        
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        # Initialize database when bot starts
        if not initialize_database():
            print("Failed to connect to database on startup. Database functionality will not work.")

bot = Bot()

@bot.event
async def on_message(message):
    print(f"Message received: {message.content} from {message.author}")
    if message.author.bot:
        print("Ignoring bot message")
        return

    print("Message is not from a bot.")
    # Check for auto-responses
    try:
        # Ensure database connection before query
        if not ensure_db_connection():
            print("Failed to ensure database connection before on_message query.")
            return
            
        print(f"Conn ID: {id(conn)}, Cursor ID: {id(cursor)}") # Debug IDs
        
        # Add a small delay before querying as a debugging step
        await asyncio.sleep(0.1)
        print("Delayed before query.")

        current_guild_id = str(message.guild.id)
        trigger_lower = message.content.lower()
        print(f"Checking database for trigger: {trigger_lower} in guild: {current_guild_id}")
        
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                      (current_guild_id, trigger_lower))
        result = cursor.fetchone()
        
        # Debug: If no result found, try querying again once immediately
        if not result:
            print("Debug: Query returned no result, trying one more time...")
            # Ensure connection is still active before re-querying
            if ensure_db_connection():
                 cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                               (current_guild_id, trigger_lower))
                 result = cursor.fetchone()
                 if result:
                     print("Debug: Re-query successful.")
                 else:
                     print("Debug: Re-query also returned no result.")
            else:
                 print("Debug: Failed to re-ensure connection for re-query.")

        if result:
            print(f"Found auto-response: trigger='{result[0]}', response='{result[1]}'")
            await message.channel.send(result[1])
            print("Sent auto-response.")
        else:
            print(f"No auto-response found for this trigger: {trigger_lower}")
            # Debug: List all triggers for this guild if none found
            try:
                # Ensure database connection before debug query
                if not ensure_db_connection():
                    print("Failed to ensure database connection before debug listing.")
                    # Continue without listing if connection fails
                else:
                    print("Debug: Executing SELECT for all triggers...")
                    # Add a small delay before debug query
                    await asyncio.sleep(0.1)
                    print("Debug: Delayed before debug query.")
                    cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?', (current_guild_id,))
                    all_responses = cursor.fetchall()
                    print(f"All triggers found for guild {current_guild_id}:")
                    if all_responses:
                        for trg, rsp in all_responses:
                            print(f"  - Trigger: '{trg}', Response: '{rsp}'")
                    else:
                        print("  (No auto-responses found for this guild at all)")
            except Exception as list_err:
                print(f"Error listing triggers for debug: {list_err}")

    except Exception as e:
        print(f"Error in auto-response processing: {e}")

    # IMPORTANT: This line is crucial to allow other commands to work
    await bot.process_commands(message)
    print("Processed commands.")

@bot.tree.command(name="addresponse", description="Add an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def addresponse(interaction: discord.Interaction, trigger: str, response: str):
    """Add an auto-response trigger."""
    print(f"Attempting to add auto-response: trigger='{trigger}', response='{response}' for guild={interaction.guild_id}")
    try:
        # Ensure database connection before insert
        print("Checking database connection...")
        if not ensure_db_connection():
            print("Database connection check failed")
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return
                
        print("Database connection verified, preparing to insert...")
        try:
            print(f"Executing INSERT OR REPLACE with values: guild_id={str(interaction.guild_id)}, trigger={trigger.lower()}, response={response}")
            cursor.execute('INSERT OR REPLACE INTO auto_responses (guild_id, trigger, response) VALUES (?, ?, ?)',
                          (str(interaction.guild_id), trigger.lower(), response))
            print("INSERT OR REPLACE executed successfully")
        except Exception as db_error:
            print(f"Database error during insert: {db_error}")
            print(f"Error type: {type(db_error).__name__}")
            await interaction.response.send_message("حدث خطأ أثناء حفظ الرد في قاعدة البيانات. يرجى المحاولة مرة أخرى.")
            return
        
        print("Attempting to commit changes...")
        try:
            # Ensure database connection before commit
            print("Verifying database connection before commit...")
            if not ensure_db_connection():
                print("Database connection verification failed before commit")
                await interaction.response.send_message("فشل الاتصال بقاعدة البيانات أثناء حفظ الرد. يرجى المحاولة مرة أخرى.")
                return
                
            print("Executing commit...")
            conn.commit()
            print("Changes committed successfully")
        except Exception as commit_error:
            print(f"Error during commit: {commit_error}")
            print(f"Error type: {type(commit_error).__name__}")
            await interaction.response.send_message("حدث خطأ أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
            return
        
        print("Sending success message to user...")
        await interaction.response.send_message(f'تم إضافة الرد التلقائي: عندما يكتب أحد "{trigger}" سيرد البوت "{response}"')
        print("Success message sent")
    except Exception as e:
        print(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        print(f"Error type: {type(e).__name__}")
        await interaction.response.send_message(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        print("Error message sent to user")

@bot.tree.command(name="removeresponse", description="Remove an auto-response trigger")
@app_commands.checks.has_permissions(manage_guild=True)
async def removeresponse(interaction: discord.Interaction, trigger: str):
    """Remove an auto-response trigger."""
    print(f"Attempting to remove auto-response: trigger='{trigger}' for guild={interaction.guild_id}")
    try:
        # Ensure database connection before delete
        if not ensure_db_connection():
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection in removeresponse.")
            return

        print("Executing DELETE...")
        cursor.execute('DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?',
                      (str(interaction.guild_id), trigger.lower()))
        print("DELETE executed.")

        print("Attempting to commit changes...")
        # Ensure database connection before commit
        if not ensure_db_connection():
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection before commit in removeresponse.")
            return
            
        conn.commit()
        print("Changes committed.")

        if cursor.rowcount > 0:
            await interaction.response.send_message(f'تم حذف الرد التلقائي "{trigger}"')
            print("Sent confirmation message for removal.")
        else:
            await interaction.response.send_message(f'لم يتم العثور على رد تلقائي بهذا المحفز "{trigger}"')
            print("Sent not found message for removal.")
    except Exception as e:
        print(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        await interaction.response.send_message(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        print("Sent error message for removal.")

@bot.tree.command(name="listresponses", description="List all auto-response triggers")
@app_commands.checks.has_permissions(manage_guild=True)
async def listresponses(interaction: discord.Interaction):
    """List all auto-response triggers."""
    print(f"Attempting to list auto-responses for guild={interaction.guild_id} (from listresponses command)")
    try:
        # Ensure database connection before query
        if not ensure_db_connection():
            await interaction.response.send_message("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection in listresponses.")
            return
                    
        print(f"Conn ID: {id(conn)}, Cursor ID: {id(cursor)}") # Debug IDs
        
        # Add a small delay before querying as a debugging step
        await asyncio.sleep(0.1)
        print("Delayed before query in listresponses.")

        print("Executing SELECT in listresponses command...")
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?',
                      (str(interaction.guild_id),))
        responses = cursor.fetchall()
        print("Executed SELECT in listresponses command.")

        # Debug: Print the raw result from the listresponses command
        # print(f"listresponses command Result: {responses}") 
            
        if responses:
            response_list = '\n'.join([f'• "{trigger}" → "{response}"' for trigger, response in responses])
            await interaction.response.send_message(f'**قائمة الردود التلقائية:**\n{response_list}')
            print("Sent list of responses from listresponses command.")
        else:
            await interaction.response.send_message('لا توجد ردود تلقائية مضافة.')
            print("Sent message indicating no responses found from listresponses command.")
    except Exception as e:
        print(f'حدث خطأ أثناء عرض الردود التلقائية في أمر listresponses: {e}') # More specific error message
        await interaction.response.send_message(f'حدث خطأ أثناء عرض الردود التلقائية: {e}')
        print("Sent error message for listing from listresponses command.")

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