import os
print("os imported")

print("Bot script started!")
import discord
print("discord imported")
from discord.ext import commands
print("commands imported")
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
            except Exception as close_err:
                print(f"Error closing existing database connection: {close_err}")
                pass
        
        conn = sqlitecloud.connect(database_url)
        cursor = conn.cursor()
        
        # Test the connection
        cursor.execute('SELECT 1')
        cursor.fetchone()
        
        # Create auto-responder table if it doesn't exist (Optional, only needed if you keep using the database for other things)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_responses (
                guild_id TEXT,
                trigger TEXT,
                response TEXT,
                PRIMARY KEY (guild_id, trigger)
            )
        ''')
        conn.commit()
        
        print("Successfully connected to the database!")
        return True
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        print("Please check your DATABASE_URL in Railway environment variables")
        return False

def ensure_db_connection():
    global conn, cursor
    if conn is None or cursor is None or not conn.is_connected():
        print("Database connection not active. Attempting to re-initialize...")
        return initialize_database()
    print("Database connection is active.")
    return True

# Initial database connection moved to on_ready
# if not initialize_database():
#     print("WARNING: Failed to connect to database on startup. The bot will continue running but auto-responses won't work.")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='-', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Initialize database when bot starts
    if not initialize_database():
        print("Failed to connect to database on startup. Database functionality will not work.")

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
            print(f"Found auto-response: {result[0]}")
            await message.channel.send(result[0])
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
        # Try to reconnect on error (ensure_db_connection handles this implicitly now)
        # time.sleep(1)  # Removed sleep to avoid blocking event loop, rely on initialize_database retry logic
        # initialize_database() # initialize_database is called above if cursor/conn is None

    # IMPORTANT: This line is crucial to allow other commands to work
    await bot.process_commands(message)
    print("Processed commands.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def addresponse(ctx, trigger: str, *, response: str):
    """Add an auto-response trigger."""
    print(f"Attempting to add auto-response: trigger='{trigger}', response='{response}' for guild={ctx.guild.id}")
    try:
        # Ensure database connection before insert
        if not ensure_db_connection():
            await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection in addresponse.")
            return
                
        print("Executing INSERT OR REPLACE...")
        cursor.execute('INSERT OR REPLACE INTO auto_responses (guild_id, trigger, response) VALUES (?, ?, ?)',
                      (str(ctx.guild.id), trigger.lower(), response))
        print("INSERT OR REPLACE executed.")
        
        print("Attempting to commit changes...")
        # Ensure database connection before commit
        if not ensure_db_connection():
            await ctx.send("فشل الاتصال بقاعدة البيانات أثناء حفظ الرد. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection before commit in addresponse.")
            return
            
        conn.commit()
        print("Changes committed.")
        
        await ctx.send(f'تم إضافة الرد التلقائي: عندما يكتب أحد "{trigger}" سيرد البوت "{response}"')
        print("Sent confirmation message.")
    except Exception as e:
        print(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        await ctx.send(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')
        print("Sent error message.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def removeresponse(ctx, trigger: str):
    """Remove an auto-response trigger."""
    print(f"Attempting to remove auto-response: trigger='{trigger}' for guild={ctx.guild.id}")
    try:
        # Ensure database connection before delete
        if not ensure_db_connection():
            await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection in removeresponse.")
            return

        print("Executing DELETE...")
        cursor.execute('DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?',
                      (str(ctx.guild.id), trigger.lower()))
        print("DELETE executed.")

        print("Attempting to commit changes...")
        # Ensure database connection before commit
        if not ensure_db_connection():
            await ctx.send("فشل الاتصال بقاعدة البيانات أثناء حفظ التغييرات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection before commit in removeresponse.")
            return
            
        conn.commit()
        print("Changes committed.")

        if cursor.rowcount > 0:
            await ctx.send(f'تم حذف الرد التلقائي "{trigger}"')
            print("Sent confirmation message for removal.")
        else:
            await ctx.send(f'لم يتم العثور على رد تلقائي بهذا المحفز "{trigger}"')
            print("Sent not found message for removal.")
    except Exception as e:
        print(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        await ctx.send(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')
        print("Sent error message for removal.")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def listresponses(ctx):
    """List all auto-response triggers."""
    print(f"Attempting to list auto-responses for guild={ctx.guild.id} (from listresponses command)")
    try:
        # Ensure database connection before query
        if not ensure_db_connection():
            await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
            print("Failed to ensure database connection in listresponses.")
            return
                    
        print(f"Conn ID: {id(conn)}, Cursor ID: {id(cursor)}") # Debug IDs
        
        # Add a small delay before querying as a debugging step
        await asyncio.sleep(0.1)
        print("Delayed before query in listresponses.")

        print("Executing SELECT in listresponses command...")
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?',
                      (str(ctx.guild.id),))
        responses = cursor.fetchall()
        print("Executed SELECT in listresponses command.")

        # Debug: Print the raw result from the listresponses command
        # print(f"listresponses command Result: {responses}") 
        # print(f"SELECT executed in listresponses command. Result: {responses}") # Print the raw result
            
        if responses:
            response_list = '\n'.join([f'• "{trigger}" → "{response}"' for trigger, response in responses])
            await ctx.send(f'**قائمة الردود التلقائية:**\n{response_list}')
            print("Sent list of responses from listresponses command.")
        else:
            await ctx.send('لا توجد ردود تلقائية مضافة.')
            print("Sent message indicating no responses found from listresponses command.")
    except Exception as e:
        print(f'حدث خطأ أثناء عرض الردود التلقائية في أمر listresponses: {e}') # More specific error message
        await ctx.send(f'حدث خطأ أثناء عرض الردود التلقائية: {e}')
        print("Sent error message for listing from listresponses command.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    """Kick a member from the server."""
    await member.kick(reason=reason)
    await ctx.send(f'{member.mention} تم طرده بنجاح!')

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    """Ban a member from the server."""
    await member.ban(reason=reason)
    await ctx.send(f'{member.mention} تم حظره بنجاح!')

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user: str):
    """Unban a user by name#discriminator."""
    banned_users = await ctx.guild.bans()
    name, discriminator = user.split('#')
    for ban_entry in banned_users:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (name, discriminator):
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f'{ban_entry.user.mention} تم فك الحظر عنه!')
            return
    await ctx.send('المستخدم غير موجود في قائمة المحظورين.')

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    """Mute a member by adding a Muted role."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, speak=False, send_messages=False, read_message_history=True, read_messages=True)
    await member.add_roles(muted_role)
    await ctx.send(f'{member.mention} تم إعطاؤه ميوت!')

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Unmute a member by removing the Muted role."""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f'{member.mention} تم فك الميوت عنه!')
    else:
        await ctx.send('المستخدم ليس عليه ميوت.')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    """Clear a number of messages (default 5)."""
    await ctx.channel.purge(limit=amount+1)
    await ctx.send(f'تم حذف {amount} رسالة!', delete_after=3)

bot.run(os.getenv('DISCORD_TOKEN')) 