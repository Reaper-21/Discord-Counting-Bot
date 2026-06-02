import discord
from discord.ext import commands
import json
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 123456789012345678  # 🔁 replace with your counting channel ID
DATA_FILE = "game.json"

# -------------------------
# INTENTS
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# DATA HANDLING
# -------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "count": 0,
            "last_user": None,
            "lives": 3,
            "paused": False,
            "last_message_id": None
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# -------------------------
# BOT READY
# -------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# -------------------------
# MESSAGE HANDLER
# -------------------------
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id != CHANNEL_ID:
        return

    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = data["count"] + 1

    # paused state (waiting for ❤️)
    if data["paused"]:
        await message.add_reaction("⏸️")
        return

    # same user twice rule
    if message.author.id == data["last_user"]:
        await handle_wrong(message, expected, "Same user cannot count twice")
        return

    # wrong number
    if number != expected:
        await handle_wrong(message, expected, "Wrong number")
        return

    # correct number
    await message.add_reaction("✅")

    data["count"] = number
    data["last_user"] = message.author.id

    # milestone every 1000
    if number % 1000 == 0:
        data["lives"] = 3
        await message.channel.send(
            f"🎉 Milestone reached: {number}! Lives restored ❤️❤️❤️"
        )

    save_data()

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

    # reset if lives reach 0
    if data["lives"] <= 0:
        data["count"] = 0
        data["lives"] = 3
        data["paused"] = False
        data["last_user"] = None

        await message.channel.send(
            "💥 Game Reset! Lives depleted. Starting again from 1."
        )

    save_data()

# -------------------------
# REACTION HANDLER (❤️ RESUME)
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

    await reaction.message.channel.send(
        f"❤️ Resumed! Next number is {data['count'] + 1}"
    )

    save_data()

# -------------------------
# RUN BOT
# -------------------------
bot.run(TOKEN)