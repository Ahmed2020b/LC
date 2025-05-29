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
                
                # Removed ticket categories table creation.
                
                # Removed ticket panels table creation.

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
    def __init__(self, categories: list[discord.CategoryChannel]):
        options = []
        for category in categories:
            options.append(discord.SelectOption(label=category.name, value=str(category.id)))

        super().__init__(
            placeholder="Choose a ticket category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category_id = int(self.values[0])
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

            # Get the selected category channel object
            selected_category = guild.get_channel(category_id)

            if not isinstance(selected_category, discord.CategoryChannel):
                 await interaction.response.send_message("Invalid category selected.", ephemeral=True)
                 return

            # Create the ticket channel within the selected category
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
                # Add staff roles here with view_channel=True
            }

            try:
                ticket_channel = await guild.create_text_channel(
                    f'ticket-{user.name}',
                    category=selected_category,  # Create the ticket in the selected category
                    overwrites=overwrites
                )

                # Store ticket information in the database
                cursor.execute('INSERT INTO tickets (guild_id, channel_id, user_id, category_name) VALUES (?, ?, ?, ?)',
                              (str(guild.id), str(ticket_channel.id), str(user.id), selected_category.name))
                conn.commit()

                # Send initial message in the ticket channel
                embed = discord.Embed(
                    title=f"New Ticket in {selected_category.name}",
                    description=f"User: {user.mention}\nCategory: {selected_category.mention}",
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
    def __init__(self, categories: list[discord.CategoryChannel]):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(categories))

# Removed commands for managing ticket categories
# @bot.tree.command(name="addticketcategory", ...)
# @bot.tree.command(name="removeticketcategory", ...)
# @bot.tree.command(name="listticketcategories", ...)

# New command to set up the ticket panel
@bot.tree.command(name="ticket-setup", description="Set up the interactive ticket panel")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="The channel to send the ticket panel to",
    title="The title of the ticket panel embed",
    description="The description of the ticket panel embed",
    color="The color of the embed (hex code, e.g., #0000ff)",
    include_server_icon="Whether to include the server icon in the embed thumbnail",
    categories="A comma-separated list of category names to include in the ticket panel"
)
async def ticket_setup(
    interaction: discord.Interaction, 
    channel: discord.TextChannel,
    title: str = "Create a Ticket", 
    description: str = "Select a category below to create a ticket.", 
    color: str = "#0000ff", 
    include_server_icon: bool = False,
    categories: str = None
):
    """Set up the interactive ticket panel."""
    guild = interaction.guild
    guild_id = str(guild.id)

    if not guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    try:
        # Get all available category channels in the guild
        all_categories = [c for c in guild.channels if isinstance(c, discord.CategoryChannel)]
        
        if not all_categories:
            await interaction.response.send_message("No categories found in this server. Please create at least one category first.", ephemeral=True)
            return

        # Filter categories based on the provided names
        selected_categories = []
        if categories:
            category_names = [name.strip() for name in categories.split(',')]
            selected_categories = [c for c in all_categories if c.name in category_names]
            
            if not selected_categories:
                await interaction.response.send_message("None of the specified categories were found. Please check the category names and try again.", ephemeral=True)
                return
        else:
            # If no categories are specified, use all of them
            selected_categories = all_categories

        # Create the embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.from_rgb(int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)) # Convert hex to RGB
        )

        if include_server_icon and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Create the view with the select menu using only the selected categories
        view = TicketPanel(selected_categories)

        # Send the message
        sent_message = await channel.send(embed=embed, view=view)

        await interaction.response.send_message(f"Ticket panel sent to {channel.mention}. The following categories are available: {', '.join([c.name for c in selected_categories])}", ephemeral=True)

    except Exception as e:
        print(f"Error sending ticket panel: {e}")
        await interaction.response.send_message("Error sending ticket panel.", ephemeral=True)

# You might want commands to close/manage tickets later, e.g.:
# @bot.tree.command(name="closeticket", description="Close the current ticket")
# @app_commands.checks.has_permissions(manage_channels=True)
# async def closeticket(interaction: discord.Interaction):
#     """Close the current ticket."""
#     pass # Implementation needed

bot.run(os.getenv('DISCORD_TOKEN')) 