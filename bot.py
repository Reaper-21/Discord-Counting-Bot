import discord
from discord.ext import commands
import json
import os
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# LOCK PER GUILD (VERY IMPORTANT)
# -------------------------
guild_locks = {}

def get_lock(guild_id):
    if guild_id not in guild_locks:
        guild_locks[guild_id] = asyncio.Lock()
    return guild_locks[guild_id]

# -------------------------
# SETTINGS
# -------------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            return json.loads(open(SETTINGS_FILE).read() or "{}")
        except:
            return {}
    return {}

settings = load_settings()

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

# -------------------------
# DATA
# -------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            return json.loads(open(DATA_FILE).read() or "{}")
        except:
            return {}
    return {}

data = load_data()

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_state(gid):
    gid = str(gid)
    if gid not in data:
        data[gid] = {"count": 0, "last_user": None, "lives": 3}
    return data[gid]

# -------------------------
# CHANNEL SETUP
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    settings[str(ctx.guild.id)] = ctx.channel.id
    save_settings()
    await ctx.send("✅ Channel set")

# -------------------------
# MAIN LOGIC (STABLE)
# -------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    gid = str(message.guild.id)

    if gid in settings and message.channel.id != settings[gid]:
        return

    if not message.content.isdigit():
        return

    async with get_lock(gid):  # 🔥 STOPS ALL DUPLICATES

        state = get_state(gid)

        number = int(message.content)
        expected = state["count"] + 1

        # RULE 1
        if state["last_user"] == message.author.id:
            await handle_wrong(message, state, expected, "Same user cannot count twice")
            save_data()
            return

        # RULE 2
        if number != expected:
            await handle_wrong(message, state, expected, "Wrong number")
            save_data()
            return

        # SUCCESS
        await message.add_reaction("✅")

        state["count"] = number
        state["last_user"] = message.author.id

        save_data()

# -------------------------
# WRONG HANDLER
# -------------------------
async def handle_wrong(message, state, expected, reason):

    state["lives"] -= 1

    await message.add_reaction("❌")

    await message.channel.send(
        f"❌ {reason}\nExpected: {expected}\nLives: {state['lives']}"
    )

    if state["lives"] <= 0:
        state["count"] = 0
        state["lives"] = 3
        state["last_user"] = None

        await message.channel.send("💥 Reset → back to 1")

# -------------------------
# START
# -------------------------
bot.run(TOKEN)