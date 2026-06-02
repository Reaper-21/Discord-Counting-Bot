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
# SAFE LOAD / SAVE
# -------------------------
def safe_load(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except:
        return default

def safe_save(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

settings = safe_load(SETTINGS_FILE, {})
data = safe_load(DATA_FILE, {})

# prevent duplicate processing
processed_messages = set()

# -------------------------
# GET GUILD STATE
# -------------------------
def get_guild(guild_id):
    gid = str(guild_id)

    if gid not in data:
        data[gid] = {
            "count": 0,
            "last_user": None,
            "lives": 3
        }

    return data[gid]

# -------------------------
# SET CHANNEL COMMAND
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    settings[str(ctx.guild.id)] = ctx.channel.id
    safe_save(SETTINGS_FILE, settings)

    await ctx.send(f"✅ Counting channel set to {ctx.channel.mention}")

# -------------------------
# MESSAGE EVENT
# -------------------------
@bot.event
async def on_message(message):

    # ignore bots
    if message.author.bot:
        return

    if not message.guild:
        return

    # prevent duplicate processing of SAME message
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)

    # keep memory small
    if len(processed_messages) > 1000:
        processed_messages.clear()

    guild_id = str(message.guild.id)
    state = get_guild(guild_id)

    # channel lock (if set)
    if guild_id in settings:
        if message.channel.id != settings[guild_id]:
            return

    # must be number
    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = state["count"] + 1

    # ❌ same user rule
    if state["last_user"] == message.author.id:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    # ❌ wrong number rule
    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    # ✅ correct number
    await message.add_reaction("✅")

    state["count"] = number
    state["last_user"] = message.author.id

    # milestone reset
    if number % 1000 == 0:
        state["lives"] = 3
        await message.channel.send(
            f"🎉 Milestone reached: {number}! Lives restored ❤️❤️❤️"
        )

    safe_save(DATA_FILE, data)

    await bot.process_commands(message)

# -------------------------
# WRONG HANDLER
# -------------------------
async def handle_wrong(message, state, expected, reason):

    state["lives"] -= 1

    await message.add_reaction("❌")

    hearts = "❤️" * max(state["lives"], 0)

    await message.channel.send(
        f"❌ {reason}\n"
        f"Expected: {expected}\n"
        f"Lives: {hearts if hearts else '0'}"
    )

    # reset game
    if state["lives"] <= 0:
        state["count"] = 0
        state["lives"] = 3
        state["last_user"] = None

        await message.channel.send("💥 Game Reset! Starting again from 1.")

    safe_save(DATA_FILE, data)

# -------------------------
# START BOT
# -------------------------
if not TOKEN:
    raise ValueError("DISCORD_TOKEN missing in environment variables")

print("Bot starting...")
bot.run(TOKEN)