import discord
import os
from discord.ext import commands, tasks
from datetime import datetime, timezone
from mcstatus import JavaServer

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # Required for on_member_join

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ====================== CONFIG ======================
YOUR_USER_ID = 668406689958985740

# Minecraft server (use "ip" or "ip:port")
MC_SERVER = "tarsmp2.playwithbao.com"  # <-- CHANGE THIS

# Channel IDs (right click channel -> Copy Channel ID, enable Developer Mode first)
GENERAL_CHANNEL_ID = 1499734536559267850  # <-- #general channel ID
WELCOME_CHANNEL_ID = 1573674577161101312  # <-- welcome channel ID (or same as general)

# ====================== ON READY ======================
@bot.event
async def on_ready():
    # Streaming status
    activity = discord.Streaming(
        name="immaculate swag",
        url="https://www.twitch.tv/qui"
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)
    print(f"[+] {bot.user} is now online and streaming | Fully Loaded")

    # Start the 5-minute Minecraft player count loop
    if not player_count_loop.is_running():
        player_count_loop.start()

# ====================== WELCOME MESSAGE ======================
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(f"Welcome to the TAR SMP server {member.mention}!")

# ====================== MINECRAFT PLAYER COUNT EVERY 5 MINS ======================
@tasks.loop(minutes=5)
async def player_count_loop():
    channel = bot.get_channel(GENERAL_CHANNEL_ID)
    if not channel:
        print("[-] Could not find #general channel")
        return

    try:
        server = JavaServer.lookup(MC_SERVER)
        status = server.status()
        online = status.players.online
        max_players = status.players.max

        await channel.send(f"**Minecraft Server Status**\nOnline Players: `{online}/{max_players}`")
    except Exception as e:
        await channel.send(f"**Minecraft Server Status**\nServer is offline or unreachable.")
        print(f"[-] MC query failed: {e}")

@player_count_loop.before_loop
async def before_player_count():
    await bot.wait_until_ready()

# Simple test command
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! `{round(bot.latency * 1000)}ms`")

# Optional: manual status check
@bot.command()
async def mc(ctx):
    try:
        server = JavaServer.lookup(MC_SERVER)
        status = server.status()
        await ctx.send(f"Online: `{status.players.online}/{status.players.max}` | Latency: `{round(status.latency)}ms`")
    except Exception as e:
        await ctx.send("Server is offline or unreachable.")

# ====================== RUN ======================
bot.run(os.getenv("DISCORD_TOKEN"))
