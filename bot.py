import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import json
from discord.ui import View, Button

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

def load_economy():
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_economy(data):
    with open(ECONOMY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_balance(user_id):
    data = load_economy()
    return data.get(str(user_id), 0)

def change_balance(user_id, amount):
    data = load_economy()
    data[str(user_id)] = data.get(str(user_id), 0) + amount
    save_economy(data)

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tickets(data):
    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_ticket(user_id, amount, issuer_id):
    data = load_tickets()
    user_tickets = data.get(str(user_id), [])
    user_tickets.append({
        'amount': amount,
        'issuer_id': issuer_id
    })
    data[str(user_id)] = user_tickets
    save_tickets(data)

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
        tickets = load_tickets().get(str(self.user_id), [])
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
        tickets.pop(self.idx)
        data = load_tickets()
        data[str(self.user_id)] = tickets
        save_tickets(data)
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
    tickets = load_tickets().get(user_id, [])
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

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 