import discord
from discord.ext import commands
import json
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
SETTINGS_FILE = "settings.json"
DATA_FILE = "game.json"

# -------------------------
# INTENTS
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# SERVER SETTINGS (CHANNEL PER GUILD)
# -------------------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(guild_channels, f, indent=4)

guild_channels = load_settings()

# -------------------------
# GAME DATA
# -------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "count": 0,
        "last_user": None,
        "lives": 3,
        "paused": False,
        "last_message_id": None
    }

def save_data():
    global data
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# -------------------------
# READY
# -------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# -------------------------
# SET CHANNEL COMMAND (ADMIN)
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    guild_channels[ctx.guild.id] = ctx.channel.id
    save_settings()

    await ctx.send(
        f"✅ Counting channel set to {ctx.channel.mention}\n"
        f"Bot will now only work here."
    )

# -------------------------
# MESSAGE EVENT
# -------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = message.guild.id

    # -------------------------
    # CHANNEL LOGIC
    # -------------------------
    if guild_id in guild_channels:
        if message.channel.id != guild_channels[guild_id]:
            return

    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = data["count"] + 1

    if data["paused"]:
        await message.add_reaction("⏸️")
        return

    if message.author.id == data["last_user"]:
        await handle_wrong(message, expected, "Same user cannot count twice")
        return

    if number != expected:
        await handle_wrong(message, expected, "Wrong number")
        return

    # correct
    await message.add_reaction("✅")

    data["count"] = number
    data["last_user"] = message.author.id

    # milestone
    if number % 1000 == 0:
        data["lives"] = 3
        await message.channel.send(
            f"🎉 Milestone reached: {number}! Lives restored ❤️❤️❤️"
        )

    save_data()

    await bot.process_commands(message)

# -------------------------
# WRONG HANDLER
# -------------------------
async def handle_wrong(message, expected, reason):

    data["lives"] -= 1
    data["paused"] = True
    data["last_message_id"] = message.id

    await message.add_reaction("❌")

    hearts = "❤️" * max(data["lives"], 0)

    await message.channel.send(
        f"❌ {reason}\n"
        f"Expected: {expected}\n"
        f"Lives: {hearts if hearts else '0'}\n\n"
        f"React ❤️ to continue from last correct number."
    )

    if data["lives"] <= 0:
        data["count"] = 0
        data["lives"] = 3
        data["paused"] = False
        data["last_user"] = None

        await message.channel.send("💥 Game Reset! Starting again from 1.")

    save_data()

# -------------------------
# REACTION EVENT
# -------------------------
@bot.event
async def on_reaction_add(reaction, user):

    if user.bot:
        return

    if not data["paused"]:
        return

    if reaction.message.id != data["last_message_id"]:
        return

    if str(reaction.emoji) != "❤️":
        return

    data["paused"] = False
    save_data()

    await reaction.message.channel.send(
        f"❤️ Resumed! Next number is {data['count'] + 1}"
    )

# -------------------------
# RUN BOT
# -------------------------
if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing in environment variables!")

print("TOKEN LOADED:", repr(TOKEN))
print("Starting bot...")

bot.run(TOKEN)