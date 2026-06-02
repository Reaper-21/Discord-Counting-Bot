import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from aiohttp import web, ClientSession

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("DISCORD_TOKEN")

# IMPORTANT:
# Put your Render URL in Environment Variables
# Example:
# https://counter-bot.onrender.com
RENDER_URL = os.getenv("RENDER_URL")

DATA_FILE = "game.json"
SETTINGS_FILE = "settings.json"

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# FILE LOCK
# =========================
file_lock = asyncio.Lock()

# =========================
# SAFE LOAD
# =========================
def safe_load(path, default):

    if not os.path.exists(path):
        return default

    try:
        with open(path, "r") as f:
            content = f.read().strip()

            if not content:
                return default

            return json.loads(content)

    except Exception as e:
        print(f"Load error {path}: {e}")
        return default


# =========================
# SAFE SAVE
# =========================
async def safe_save(path, obj):

    async with file_lock:

        def write():
            with open(path, "w") as f:
                json.dump(obj, f, indent=4)

        await asyncio.to_thread(write)


# =========================
# LOAD DATA
# =========================
settings = safe_load(SETTINGS_FILE, {})
data = safe_load(DATA_FILE, {})

# =========================
# PER SERVER STATE
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
# SET CHANNEL
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):

    settings[str(ctx.guild.id)] = ctx.channel.id

    await safe_save(
        SETTINGS_FILE,
        settings
    )

    await ctx.send(
        f"✅ Counting channel set to {ctx.channel.mention}"
    )


# =========================
# SHOW STATUS
# =========================
@bot.command()
async def count(ctx):

    state = get_state(ctx.guild.id)

    await ctx.send(
        f"📊 Current Count: {state['count']}\n"
        f"❤️ Lives: {state['lives']}"
    )


# =========================
# MESSAGE EVENT
# =========================
@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = str(message.guild.id)

    state = get_state(message.guild.id)

    # Process commands first
    await bot.process_commands(message)

    # Restrict counting channel if set
    if guild_id in settings:

        if message.channel.id != settings[guild_id]:
            return

    if not message.content.isdigit():
        return

    number = int(message.content)

    expected = state["count"] + 1

    # -------------------------
    # WRONG NUMBER FIRST
    # -------------------------
    if number != expected:

        await handle_wrong(
            message,
            state,
            expected,
            "Wrong number"
        )

        return

    # -------------------------
    # SAME USER RULE
    # -------------------------
    if state["last_user"] == message.author.id:

        await handle_wrong(
            message,
            state,
            expected,
            "Same user cannot count twice"
        )

        return

    # -------------------------
    # CORRECT NUMBER
    # -------------------------
    state["count"] = number
    state["last_user"] = message.author.id

    try:
        await message.add_reaction("✅")
    except:
        pass

    # Milestone restore
    if number % 1000 == 0:

        state["lives"] = 3

        await message.channel.send(
            f"🎉 Milestone {number} reached!\n"
            f"❤️ Lives restored."
        )

    await safe_save(DATA_FILE, data)


# =========================
# WRONG HANDLER
# =========================
async def handle_wrong(
    message,
    state,
    expected,
    reason
):

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

    if state["lives"] <= 0:

        state["count"] = 0
        state["last_user"] = None
        state["lives"] = 3

        await message.channel.send(
            "💥 Game Reset!\n"
            "Start again from 1."
        )

    await safe_save(DATA_FILE, data)


# =========================
# KEEP ALIVE WEB SERVER
# =========================
async def start_web():

    app = web.Application()

    async def home(request):
        return web.Response(
            text="Counter Bot Online"
        )

    app.router.add_get("/", home)

    port = int(
        os.getenv("PORT", 10000)
    )

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"Web server started on {port}")


# =========================
# SELF PING EVERY 10 MIN
# =========================
@tasks.loop(minutes=10)
async def self_ping():

    if not RENDER_URL:
        return

    try:

        async with ClientSession() as session:

            async with session.get(RENDER_URL) as resp:

                print(
                    f"Self Ping: {resp.status}"
                )

    except Exception as e:

        print(
            f"Self Ping Failed: {e}"
        )


# =========================
# READY
# =========================
@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )

    if not self_ping.is_running():
        self_ping.start()


# =========================
# ERROR HANDLER
# =========================
@bot.event
async def on_error(event, *args, **kwargs):

    print(f"Error in {event}")


# =========================
# MAIN
# =========================
async def main():

    await start_web()

    await bot.start(TOKEN)


if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN missing"
    )

print("Starting Counter Bot...")

asyncio.run(main())