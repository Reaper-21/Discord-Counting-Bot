import discord
from discord.ext import commands
import json
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

intents = discord.Intents.default()
intents.message_content = True

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
# GAME DATA (SAFE + MULTI-SERVER)
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
    gid = str(guild_id)

    if gid not in data:
        data[gid] = {
            "count": 0,
            "last_user": None,
            "lives": 3
        }

    # safety repair (prevents broken states)
    if "count" not in data[gid]:
        data[gid]["count"] = 0
    if "last_user" not in data[gid]:
        data[gid]["last_user"] = None
    if "lives" not in data[gid]:
        data[gid]["lives"] = 3

    return data[gid]

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

    # prevent same user twice
    if state["last_user"] is not None and message.author.id == state["last_user"]:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    # wrong number
    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    # correct number
    await message.add_reaction("✅")

    state["count"] = number
    state["last_user"] = message.author.id

    # milestone reward
    if number % 1000 == 0:
        state["lives"] = 3
        await message.channel.send(
            f"🎉 Milestone reached: {number}! Lives restored ❤️❤️❤️"
        )

    save_data()
    await bot.process_commands(message)

# -------------------------
# WRONG HANDLER (NO PAUSE SYSTEM)
# -------------------------
async def handle_wrong(message, state, expected, reason):

    state["lives"] -= 1

    await message.add_reaction("❌")

    hearts = "❤️" * max(state["lives"], 0)

    await message.channel.send(
        f"❌ {reason}\n"
        f"Expected: {expected}\n"
        f"Lives left: {hearts if hearts else '0'}"
    )

    # reset game if no lives
    if state["lives"] <= 0:
        state["count"] = 0
        state["lives"] = 3
        state["last_user"] = None

        await message.channel.send("💥 Game Reset! Starting again from 1.")

    save_data()

# -------------------------
# START BOT
# -------------------------
if not TOKEN:
    raise ValueError("DISCORD_TOKEN missing in environment variables")

print("Bot starting...")
bot.run(TOKEN)