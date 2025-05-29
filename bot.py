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
                
                # Create ticket categories table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ticket_categories (
                        guild_id TEXT,
                        category_name TEXT,
                        description TEXT,
                        emoji TEXT,
                        PRIMARY KEY (guild_id, category_name)
                    )
                ''')

                # Create ticket panels table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ticket_panels (
                        guild_id TEXT,
                        channel_id TEXT,
                        message_id TEXT UNIQUE,
                        PRIMARY KEY (guild_id, message_id)
                    )
                ''')

                # Create tickets table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tickets (
                        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT,
                        channel_id TEXT UNIQUE,
                        user_id TEXT,
                        category_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'open'
                    )
                ''')
                
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
    # Defer the interaction to prevent timeout
    await interaction.response.defer(ephemeral=True)

    try:
        # Purge messages
        deleted = await interaction.channel.purge(limit=amount + 1)
        # Send a follow-up message after the purge is complete
        await interaction.followup.send(f'تم حذف {len(deleted) - 1} رسالة!', ephemeral=True)
    except Exception as e:
        print(f"Error clearing messages: {e}")
        try:
            await interaction.followup.send("حدث خطأ أثناء حذف الرسائل.", ephemeral=True)
        except:
            pass # Ignore if sending error message fails

# --- Ticket System --- #

class TicketCategorySelect(discord.ui.Select):
    def __init__(self, categories):
        options = []
        for cat in categories:
            try:
                # Ensure emoji is valid or None
                emoji = None
                if cat[2]: # Check if emoji string exists
                    # Try getting custom emoji
                    emoji = discord.utils.get(bot.emojis, name=cat[2].strip(':'))
                    # If not custom, try getting partial emoji
                    if not emoji:
                        try:
                            emoji = discord.PartialEmoji.from_str(cat[2])
                        except:
                            pass # Ignore if parsing fails
                            
                options.append(discord.SelectOption(label=cat[0], description=cat[1], emoji=emoji))
            except Exception as e:
                print(f"Error creating select option for category {cat[0]}: {e}")
                options.append(discord.SelectOption(label=cat[0], description=cat[1])) # Add without emoji if error

        super().__init__(
            placeholder="Choose a ticket category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0]
        guild = interaction.guild
        user = interaction.user

        if not guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        # Check if the user already has an open ticket
        if ensure_db_connection():
            cursor.execute("SELECT channel_id FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'", (str(guild.id), str(user.id)))
            existing_ticket = cursor.fetchone()
            if existing_ticket:
                await interaction.response.send_message(f"You already have an open ticket in <#{existing_ticket[0]}>.", ephemeral=True)
                return

            # Get category details from the database
            cursor.execute('SELECT description FROM ticket_categories WHERE guild_id = ? AND category_name = ?', (str(guild.id), category_name))
            category_details = cursor.fetchone()
            category_description = category_details[0] if category_details else "No description provided."

            # Create the ticket channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
                # Add staff roles here with view_channel=True
            }

            try:
                ticket_channel = await guild.create_text_channel(
                    f'ticket-{category_name}-{user.name}',
                    category=discord.utils.get(guild.categories, name='Tickets'), # Optional: Specify a Ticket Category Group
                    overwrites=overwrites
                )

                # Store ticket information in the database
                cursor.execute('INSERT INTO tickets (guild_id, channel_id, user_id, category_name) VALUES (?, ?, ?, ?)',
                              (str(guild.id), str(ticket_channel.id), str(user.id), category_name))
                conn.commit()

                # Send initial message in the ticket channel
                embed = discord.Embed(
                    title=f"New Ticket - {category_name}",
                    description=f"User: {user.mention}\nCategory: {category_name}\nDescription: {category_description}",
                    color=discord.Color.blue()
                )
                await ticket_channel.send(embed=embed)

                await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

            except Exception as e:
                print(f"Error creating ticket channel: {e}")
                await interaction.response.send_message("There was an error creating your ticket. Please try again later.", ephemeral=True)
        else:
            await interaction.response.send_message("Database connection failed. Cannot create ticket at this time.", ephemeral=True)

class TicketPanel(discord.ui.View):
    def __init__(self, categories):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(categories))

# Commands for managing ticket categories
@bot.tree.command(name="addticketcategory", description="Add a ticket category for the panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def addticketcategory(interaction: discord.Interaction, name: str, description: str, emoji: str = None):
    """Add a ticket category for the panel."""
    guild_id = str(interaction.guild_id)
    try:
        if not ensure_db_connection():
            await interaction.response.send_message("Database connection failed.", ephemeral=True)
            return

        cursor.execute('INSERT OR REPLACE INTO ticket_categories (guild_id, category_name, description, emoji) VALUES (?, ?, ?, ?)',
                      (guild_id, name, description, emoji))
        conn.commit()
        await interaction.response.send_message(f"Ticket category '{name}' added/updated.", ephemeral=True)
    except Exception as e:
        print(f"Error adding ticket category: {e}")
        await interaction.response.send_message("Error adding ticket category.", ephemeral=True)

@bot.tree.command(name="removeticketcategory", description="Remove a ticket category")
@app_commands.checks.has_permissions(manage_guild=True)
async def removeticketcategory(interaction: discord.Interaction, name: str):
    """Remove a ticket category."""
    guild_id = str(interaction.guild_id)
    try:
        if not ensure_db_connection():
            await interaction.response.send_message("Database connection failed.", ephemeral=True)
            return

        cursor.execute('DELETE FROM ticket_categories WHERE guild_id = ? AND category_name = ?',
                      (guild_id, name))
        conn.commit()
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"Ticket category '{name}' removed.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Ticket category '{name}' not found.", ephemeral=True)
    except Exception as e:
        print(f"Error removing ticket category: {e}")
        await interaction.response.send_message("Error removing ticket category.", ephemeral=True)

@bot.tree.command(name="listticketcategories", description="List all ticket categories")
@app_commands.checks.has_permissions(manage_guild=True)
async def listticketcategories(interaction: discord.Interaction):
    """List all ticket categories."""
    guild_id = str(interaction.guild_id)
    try:
        if not ensure_db_connection():
            await interaction.response.send_message("Database connection failed.", ephemeral=True)
            return

        cursor.execute('SELECT category_name, description, emoji FROM ticket_categories WHERE guild_id = ?', (guild_id,))
        categories = cursor.fetchall()

        if categories:
            response_message = "**Ticket Categories:**\n"
            for name, desc, emoji in categories:
                response_message += f"• {emoji if emoji else ''} **{name}**: {desc}\n"
            await interaction.response.send_message(response_message, ephemeral=True)
        else:
            await interaction.response.send_message("No ticket categories added yet.", ephemeral=True)
    except Exception as e:
        print(f"Error listing ticket categories: {e}")
        await interaction.response.send_message("Error listing ticket categories.", ephemeral=True)

# Command to send the ticket panel
@bot.tree.command(name="sendticketpanel", description="Send the interactive ticket panel to a channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def sendticketpanel(interaction: discord.Interaction, channel: discord.TextChannel, title: str = "Create a Ticket", description: str = "Select a category below to create a ticket.", color: str = "#0000ff", include_server_icon: bool = False):
    """Send the interactive ticket panel to a channel."""
    guild = interaction.guild
    guild_id = str(guild.id)

    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    try:
        if not ensure_db_connection():
            await interaction.response.send_message("Database connection failed.", ephemeral=True)
            return

        # Get categories for the select menu
        cursor.execute('SELECT category_name, description, emoji FROM ticket_categories WHERE guild_id = ?', (guild_id,))
        categories = cursor.fetchall()

        if not categories:
            await interaction.response.send_message("Please add ticket categories using `/addticketcategory` before sending the panel.", ephemeral=True)
            return

        # Create the embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)) # Convert hex to RGB
        )

        if include_server_icon and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Create the view with the select menu
        view = TicketPanel(categories)

        # Send the message
        sent_message = await channel.send(embed=embed, view=view)

        # Store panel message info in database
        cursor.execute('INSERT OR REPLACE INTO ticket_panels (guild_id, channel_id, message_id) VALUES (?, ?, ?)',
                      (guild_id, str(channel.id), str(sent_message.id)))
        conn.commit()

        await interaction.response.send_message(f"Ticket panel sent to {channel.mention}", ephemeral=True)

    except Exception as e:
        print(f"Error sending ticket panel: {e}")
        await interaction.response.send_message("Error sending ticket panel.", ephemeral=True)

bot.run(os.getenv('DISCORD_TOKEN')) 