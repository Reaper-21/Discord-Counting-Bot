import discord
from discord.ext import commands
import json
import os

# -------------------------
# CONFIG
# -------------------------
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1511334288082079845  # <-- CHANGE THIS

DATA_FILE = "game.json"

# -------------------------
# INTENTS
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# SAFE DATA LOAD
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

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "count": 0,
            "last_user": None,
            "lives": 3,
            "paused": False,
            "last_message_id": None
        }

def save_data():
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
# MESSAGE EVENT
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

    await reaction.message.channel.send(
        f"❤️ Resumed! Next number is {data['count'] + 1}"
    )

    save_data()

# -------------------------
# RUN BOT
# -------------------------
if not TOKEN:
    print("ERROR: TOKEN not found in environment variables!")

bot.run(TOKEN)