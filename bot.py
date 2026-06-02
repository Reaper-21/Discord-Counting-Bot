import discord
from discord.ext import commands
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# -------------------------
# TOKEN
# -------------------------
TOKEN = os.getenv("DISCORD_TOKEN")

# -------------------------
# FILES
# -------------------------
DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

# -------------------------
# INTENTS
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# SIMPLE WEB SERVER (RENDER FIX)
# -------------------------
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# -------------------------
# SAFE LOAD/SAVE
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

# prevent duplicate message handling
processed_messages = set()

# -------------------------
# GUILD STATE
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

    if message.author.bot:
        return

    if not message.guild:
        return

    # prevent duplicate handling
    if message.id in processed_messages:
        return
    processed_messages.add(message.id)

    if len(processed_messages) > 1000:
        processed_messages.clear()

    guild_id = str(message.guild.id)
    state = get_guild(guild_id)

    # channel lock
    if guild_id in settings:
        if message.channel.id != settings[guild_id]:
            return

    # must be number
    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = state["count"] + 1

    # same user rule
    if state["last_user"] == message.author.id:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    # wrong number rule
    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    # correct
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