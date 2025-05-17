import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
from discord.ui import View, Button
import sqlitecloud

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Needed to DM users
bot = commands.Bot(command_prefix='-', intents=intents)

ROLE_ID = 1373351745102549082  # Replace with your actual role ID

ECONOMY_FILE = 'economy.json'
TICKETS_FILE = 'tickets.json'

SQLITECLOUD_URL = os.getenv("SQLITECLOUD_URL")

def get_db_connection():
    return sqlitecloud.connect(SQLITECLOUD_URL)

def load_economy():
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_economy(data):
    with open(ECONOMY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_balance(user_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT balance FROM economy WHERE user_id = ?', (str(user_id),))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def change_balance(user_id, amount):
    conn = get_db_connection()
    cur = conn.execute('SELECT balance FROM economy WHERE user_id = ?', (str(user_id),))
    row = cur.fetchone()
    if row:
        conn.execute('UPDATE economy SET balance = balance + ? WHERE user_id = ?', (amount, str(user_id)))
    else:
        conn.execute('INSERT INTO economy (user_id, balance) VALUES (?, ?)', (str(user_id), amount))
    conn.commit()
    conn.close()

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tickets(data):
    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_ticket(user_id, amount, issuer_id):
    conn = get_db_connection()
    conn.execute('INSERT INTO tickets (user_id, amount, issuer_id) VALUES (?, ?, ?)', (str(user_id), amount, str(issuer_id)))
    conn.commit()
    conn.close()

def get_tickets(user_id):
    conn = get_db_connection()
    cur = conn.execute('SELECT id, amount, issuer_id FROM tickets WHERE user_id = ?', (str(user_id),))
    tickets = [{'id': row[0], 'amount': row[1], 'issuer_id': row[2]} for row in cur.fetchall()]
    conn.close()
    return tickets

def remove_ticket(ticket_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()

class TicketPayView(View):
    def __init__(self, user_id, tickets):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tickets = tickets
        for idx, ticket in enumerate(tickets, 1):
            label = f"مخالفة #{idx} ({ticket['amount']} ريال)"
            self.add_item(TicketPayButton(label=label, idx=idx-1, user_id=user_id))

class TicketPayButton(Button):
    def __init__(self, label, idx, user_id):
        super().__init__(label=label, style=discord.ButtonStyle.green)
        self.idx = idx
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('هذا الزر ليس لك.', ephemeral=True)
            return
        tickets = get_tickets(self.user_id)
        if self.idx >= len(tickets):
            await interaction.response.send_message('هذه المخالفة لم تعد موجودة.', ephemeral=True)
            return
        ticket = tickets[self.idx]
        balance = get_balance(self.user_id)
        if balance < int(ticket['amount']):
            await interaction.response.send_message(f'رصيدك غير كافٍ لدفع هذه المخالفة. رصيدك الحالي: {balance} ريال', ephemeral=True)
            return
        # Pay the ticket
        change_balance(self.user_id, -int(ticket['amount']))
        remove_ticket(ticket['id'])
        await interaction.response.send_message(f'تم دفع مخالفة بقيمة {ticket["amount"]} ريال بنجاح! رصيدك الحالي: {get_balance(self.user_id)} ريال', ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='رصد')
async def rasad(ctx, member: discord.Member = None, amount: str = None):
    """Sends a customizable DM to the mentioned user with the specified amount as a traffic ticket. Only users with the specified role can use this command."""
    role = discord.utils.get(ctx.author.roles, id=ROLE_ID)
    if role is None:
        await ctx.send('ليس لديك الصلاحية لاستخدام هذا الأمر.')
        return
    if member is None or amount is None or not amount.isdigit():
        await ctx.send('Usage: -رصد @user amount')
        return
    amount = int(amount)
    add_ticket(member.id, amount, ctx.author.id)
    embed = discord.Embed(title='🚨 إشعار مخالفة مرورية 🚨',
                          description=f'عزيزي {member.mention},\nلقد تم رصد مخالفة مرورية بقيمة: {amount} ريال.\nيرجى مراجعة الإدارة للمزيد من التفاصيل.',
                          color=0xff0000)
    embed.set_image(url='https://cdn.discordapp.com/attachments/1372938634390667395/1373291606131736636/2F2740FA-A534-4205-B756-89AEC7DAF65B.jpg?ex=6829e0f9&is=68288f79&hm=f9002de01279f0ee64c514a294b94a1ce6b3e5bffd911d83d304a0e17cca0308&')  # Replace with your image URL
    try:
        await member.send(embed=embed)
        await ctx.send(f'تم إضافة المخالفة إلى {member.mention} بنجاح.')
    except Exception as e:
        await ctx.send(f'لم أستطع إرسال رسالة خاصة إلى {member.mention}. تأكد أن الرسائل الخاصة مفعلة لديه.')

@bot.command(name='رصيدي')
async def my_balance(ctx):
    balance = get_balance(ctx.author.id)
    await ctx.send(f'رصيدك الحالي: {balance} ريال')

@bot.command(name='مخالفاتي')
async def my_tickets(ctx):
    user_id = str(ctx.author.id)
    tickets = get_tickets(user_id)
    if not tickets:
        await ctx.send('ليس لديك مخالفات حالياً.')
        return
    embed = discord.Embed(title='مخالفاتك المرورية', color=0xffa500)
    for idx, ticket in enumerate(tickets, 1):
        issuer = await bot.fetch_user(ticket['issuer_id'])
        embed.add_field(name=f'مخالفة #{idx}', value=f"القيمة: {ticket['amount']} ريال\nالجهة: {issuer.mention}", inline=False)
    try:
        await ctx.author.send(embed=embed, view=TicketPayView(ctx.author.id, tickets))
        await ctx.send('تم إرسال قائمة مخالفاتك في الخاص.')
    except Exception:
        await ctx.send('لم أستطع إرسال رسالة خاصة. تأكد أن رسائلك الخاصة مفعلة.')

@bot.command(name='dbtest')
async def dbtest(ctx, tablename: str):
    """Fetches the first row from the given table in SQLiteCloud and prints it."""
    try:
        conn = get_db_connection()
        cursor = conn.execute(f'SELECT * FROM {tablename} LIMIT 1;')
        result = cursor.fetchone()
        await ctx.send(f'First row in {tablename}: {result}')
        conn.close()
    except Exception as e:
        await ctx.send(f'Error: {e}')

# Ensure tables exist on startup

def ensure_tables():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS economy (user_id TEXT PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, amount INTEGER, issuer_id TEXT)''')
    conn.commit()
    conn.close()

ensure_tables()

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 