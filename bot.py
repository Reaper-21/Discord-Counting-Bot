import discord
from discord.ext import commands
import json
import os
import asyncio
from aiohttp import web

# =========================
# CONFIG
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
# SAFE FILE HANDLING
# =========================
lock = asyncio.Lock()

def safe_load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except:
        return default

async def safe_save(path, data):
    async with lock:
        def _write():
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        await asyncio.to_thread(_write)

settings = safe_load(SETTINGS_FILE, {})
data = safe_load(DATA_FILE, {})

# =========================
# GET / INIT GUILD STATE
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
    await safe_save(SETTINGS_FILE, settings)

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

    # channel restriction
    if gid in settings and message.channel.id != settings[gid]:
        return

    if not message.content.isdigit():
        return

    number = int(message.content)
    expected = state["count"] + 1

    # =========================
    # ORDER FIX (IMPORTANT)
    # =========================

    # 1. WRONG NUMBER CHECK FIRST
    if number != expected:
        await handle_wrong(message, state, expected, "Wrong number")
        return

    # 2. SAME USER CHECK AFTER VALID NUMBER
    # (prevents spam triggering when already wrong)
    if message.author.id == state["last_user"]:
        await handle_wrong(message, state, expected, "Same user cannot count twice")
        return

    # =========================
    # CORRECT NUMBER
    # =========================
    state["count"] = number
    state["last_user"] = message.author.id

    try:
        await message.add_reaction("✅")
    except:
        pass

    await safe_save(DATA_FILE, data)

    await bot.process_commands(message)

# =========================
# WRONG HANDLER (STABLE)
# =========================
async def handle_wrong(message, state, expected, reason):

    state["lives"] -= 1

    try:
        await message.add_reaction("❌")
    except:
        pass

    hearts = "❤️" * max(state["lives"], 0)

    await message.channel.send(
        f"❌ {reason}\n"
        f"Expected: {expected}\n"
        f"Lives: {hearts if hearts else '0'}"
    )

    # RESET
    if state["lives"] <= 0:
        state["count"] = 0
        state["lives"] = 3
        state["last_user"] = None

        await message.channel.send("💥 Game Reset! Starting again from 1.")

    await safe_save(DATA_FILE, data)

# =========================
# ERROR HANDLING (CRASH PROTECTION)
# =========================
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"[ERROR] in {event}")

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# =========================
# WEB SERVER (RENDER FIX)
# =========================
async def start_web():
    app = web.Application()

    async def health(request):
        return web.Response(text="OK")

    app.router.add_get("/", health)

    port = int(os.getenv("PORT", 10000))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Web server running on port {port}")

# =========================
# MAIN START
# =========================
async def main():
    await start_web()
    await bot.start(TOKEN)

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is missing")

print("Bot starting...")
asyncio.run(main())