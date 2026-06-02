import discord
from discord.ext import commands
import json
import os
from aiohttp import web
import asyncio

# =========================
# ENV
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# FILE SAFE LOAD
# =========================
def safe_load(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

settings = safe_load(SETTINGS_FILE, {})
data = safe_load(DATA_FILE, {})

# =========================
# PER GUILD STATE
# =========================
def get_state(guild_id):
    gid = str(guild_id)

    if gid not in data:
        data[gid] = {
            "count": 0,
            "last_user": None,
            "lives": 3
        }

    return data[gid]

# =========================
# SET CHANNEL COMMAND
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    settings[str(ctx.guild.id)] = ctx.channel.id
    save_json(SETTINGS_FILE, settings)
    await ctx.send(f"✅ Counting channel set to {ctx.channel.mention}")

# =========================
# MESSAGE EVENT
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    gid = str(message.guild.id)
    state = get_state(message.guild.id)

    # channel lock (optional)
    if gid in settings:
        if message.channel.id != settings[gid]:
            return

    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = state["count"] + 1

    # ❌ same user rule (FIXED: checked FIRST, but only if number is correct)
    if message.author.id == state["last_user"]:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    # ❌ wrong number
    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    # ✅ correct
    await message.add_reaction("✅")

    state["count"] = number
    state["last_user"] = message.author.id

    save_json(DATA_FILE, data)

    await bot.process_commands(message)

# =========================
# WRONG HANDLER (NO PAUSE)
# =========================
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

    save_json(DATA_FILE, data)

# =========================
# WEB SERVER (FIX RENDER SLEEP ISSUE)
# =========================
async def start_web():
    app = web.Application()

    async def home(request):
        return web.Response(text="Bot is alive")

    app.router.add_get("/", home)

    port = int(os.getenv("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Web server running on port {port}")

# =========================
# STARTUP
# =========================
async def main():
    await start_web()
    await bot.start(TOKEN)

if not TOKEN:
    raise ValueError("DISCORD_TOKEN missing")

print("Bot starting...")
asyncio.run(main())