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
print("dotenv imported")
print("sqlitecloud and time imported")

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

# Removed auto-responder on_message event
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check for auto-responses
    try:
        global cursor, conn # Added conn to global here as well
        if cursor is None or conn is None or not conn.is_connected(): # Added conn check
            print("Database connection is not initialized or lost. Attempting to reconnect...")
            if not initialize_database():
                print("Failed to reconnect to database. Cannot process auto-response.")
                return
            
        cursor.execute('SELECT response FROM auto_responses WHERE guild_id = ? AND trigger = ?', 
                      (str(message.guild.id), message.content.lower()))
        result = cursor.fetchone()
        if result:
            await message.channel.send(result[0])
    except Exception as e:
        print(f"Error in auto-response: {e}")
        # Try to reconnect on error
        # time.sleep(1)  # Removed sleep to avoid blocking event loop, rely on initialize_database retry logic
        # initialize_database() # initialize_database is called above if cursor/conn is None

    await bot.process_commands(message)

# Removed auto-responder commands
@bot.command()
@commands.has_permissions(manage_guild=True)
async def addresponse(ctx, trigger: str, *, response: str):
    """Add an auto-response trigger."""
    try:
        global cursor, conn # Added conn to global here as well
        if cursor is None or conn is None or not conn.is_connected(): # Added conn check
            if not initialize_database():
                await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
                return
                
        cursor.execute('INSERT OR REPLACE INTO auto_responses (guild_id, trigger, response) VALUES (?, ?, ?)',
                      (str(ctx.guild.id), trigger.lower(), response))
        conn.commit()
        await ctx.send(f'تم إضافة الرد التلقائي: عندما يكتب أحد "{trigger}" سيرد البوت "{response}"')
    except Exception as e:
        await ctx.send(f'حدث خطأ أثناء إضافة الرد التلقائي: {e}')

@bot.command()
@commands.has_permissions(manage_guild=True)
async def removeresponse(ctx, trigger: str):
    """Remove an auto-response trigger."""
    try:
        global cursor, conn # Added conn to global here as well
        if cursor is None or conn is None or not conn.is_connected(): # Added conn check
            if not initialize_database():
                await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
                return
                
        cursor.execute('DELETE FROM auto_responses WHERE guild_id = ? AND trigger = ?',
                      (str(ctx.guild.id), trigger.lower()))
        conn.commit()
        if cursor.rowcount > 0:
            await ctx.send(f'تم حذف الرد التلقائي "{trigger}"')
        else:
            await ctx.send(f'لم يتم العثور على رد تلقائي بهذا المحفز "{trigger}"')
    except Exception as e:
        await ctx.send(f'حدث خطأ أثناء حذف الرد التلقائي: {e}')

@bot.command()
@commands.has_permissions(manage_guild=True)
async def listresponses(ctx):
    """List all auto-response triggers."""
    try:
        global cursor, conn # Added conn to global here as well
        if cursor is None or conn is None or not conn.is_connected(): # Added conn check
            if not initialize_database():
                await ctx.send("فشل الاتصال بقاعدة البيانات. يرجى المحاولة مرة أخرى.")
                return
                
        cursor.execute('SELECT trigger, response FROM auto_responses WHERE guild_id = ?',
                      (str(ctx.guild.id),))
        responses = cursor.fetchall()
        if responses:
            response_list = '\n'.join([f'• "{trigger}" → "{response}"' for trigger, response in responses])
            await ctx.send(f'**قائمة الردود التلقائية:**\n{response_list}')
        else:
            await ctx.send('لا توجد ردود تلقائية مضافة.')
    except Exception as e:
        await ctx.send(f'حدث خطأ أثناء عرض الردود التلقائية: {e}')

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