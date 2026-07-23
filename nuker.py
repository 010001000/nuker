import discord
import os
from discord.ext import commands
from datetime import datetime, timezone

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ====================== CONFIG ======================
YOUR_USER_ID = 668406689958985740

# ====================== ON READY ======================
@bot.event
async def on_ready():
    # Streaming status
    activity = discord.Streaming(
        name="qui on top",
        url="https://www.twitch.tv/qui"  # Change if you want
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)
    print(f"[+] {bot.user} is now online and streaming | Fully Loaded")

# Simple test command (optional - you can remove)
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! `{round(bot.latency * 1000)}ms`")

# ====================== RUN ======================
bot.run(os.getenv("DISCORD_TOKEN"))
