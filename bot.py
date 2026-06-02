import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# SETTINGS (per server channel)
# -------------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except:
            return {}
    return {}

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

settings = load_settings()

# -------------------------
# GAME STATE (PER SERVER FIX)
# -------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except:
            return {}

    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

def get_guild(guild_id):
    if str(guild_id) not in data:
        data[str(guild_id)] = {
            "count": 0,
            "last_user": None,
            "lives": 3,
            "paused": False,
            "last_message_id": None
        }
    return data[str(guild_id)]

# -------------------------
# SET CHANNEL COMMAND
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    settings[str(ctx.guild.id)] = ctx.channel.id
    save_settings()

    await ctx.send(f"✅ Counting channel set to {ctx.channel.mention}")

# -------------------------
# MESSAGE EVENT
# -------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = str(message.guild.id)
    state = get_guild(guild_id)

    # channel lock
    if guild_id in settings:
        if message.channel.id != settings[guild_id]:
            return

    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = state["count"] + 1

    # paused check (PER SERVER NOW)
    if state["paused"]:
        await message.add_reaction("⏸️")
        return

    if message.author.id == state["last_user"]:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    await message.add_reaction("✅")

    state["count"] = number
    state["last_user"] = message.author.id

    if number % 1000 == 0:
        state["lives"] = 3
        await message.channel.send(f"🎉 Milestone {number}! Lives restored ❤️❤️❤️")

    save_data()
    await bot.process_commands(message)

# -------------------------
# WRONG HANDLER (FIXED)
# -------------------------
async def handle_wrong(message, state, expected, reason):

    state["lives"] -= 1
    state["paused"] = True
    state["last_message_id"] = message.id

    await message.add_reaction("❌")

    hearts = "❤️" * max(state["lives"], 0)

    await message.channel.send(
        f"❌ {reason}\n"
        f"Expected: {expected}\n"
        f"Lives: {hearts if hearts else '0'}\n\n"
        f"React ❤️ to continue."
    )

    if state["lives"] <= 0:
        state["count"] = 0
        state["lives"] = 3
        state["paused"] = False
        state["last_user"] = None

        await message.channel.send("💥 Game Reset!")

    save_data()

# -------------------------
# REACTION FIX (IMPORTANT)
# -------------------------
@bot.event
async def on_reaction_add(reaction, user):

    if user.bot:
        return

    guild_id = str(reaction.message.guild.id)
    state = get_guild(guild_id)

    if not state["paused"]:
        return

    if reaction.message.id != state["last_message_id"]:
        return

    if str(reaction.emoji) != "❤️":
        return

    state["paused"] = False
    save_data()

    await reaction.message.channel.send(
        f"❤️ Resumed! Next number: {state['count'] + 1}"
    )

# -------------------------
# START
# -------------------------
if not TOKEN:
    raise ValueError("Missing DISCORD_TOKEN")

print("Bot starting...")
bot.run(TOKEN)