import discord
import re
import json
import os
import threading
import sys

version = "3.3 HF2"
TOKEN = os.getenv("DISCORD_BOT_TOKEN") 

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

pattern_disconnect = re.compile(
    r'(stuck(?: at)?\s*)?["\']?(ok|okay)\s+to\s+disconnect["\']?',
    re.IGNORECASE
)

# Theme creation intent detection
pattern_theme = re.compile(
    r'(?:(replace).*(wallpaper|assets?|theme|icon)|'
    r'(create).*(theme|themes|custom themes|cfw)|'
    r'(make).*(theme|themes|custom themes|cfw))',
    re.IGNORECASE
)

COUNT_FILE = "solved_count.json"
ENABLED_FILE = "bot_enabled.flag"
ACTIVITY_FILE = "bot_status.txt"
USER_STATUS_FILE = "bot_user_status.txt"

def load_solved_count():
    if os.path.exists(COUNT_FILE):
        try:
            with open(COUNT_FILE, "r") as f:
                return json.load(f).get("count", 0)
        except json.JSONDecodeError:
            return 0
    return 0

def save_solved_count(count):
    with open(COUNT_FILE, "w") as f:
        json.dump({"count": count}, f)

def load_bot_enabled():
    return os.path.exists(ENABLED_FILE)

def set_bot_enabled(enabled: bool):
    if enabled:
        open(ENABLED_FILE, "w").close()
    else:
        if os.path.exists(ENABLED_FILE):
            os.remove(ENABLED_FILE)

def load_custom_status():
    if os.path.exists(ACTIVITY_FILE):
        with open(ACTIVITY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_custom_status(text):
    with open(ACTIVITY_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())

def load_user_status():
    if os.path.exists(USER_STATUS_FILE):
        with open(USER_STATUS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""

def save_user_status(text):
    with open(USER_STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(text.strip())

solved_count = load_solved_count()

REPLY_DISCONNECT = """
> ### ℹ️ **If your iPod shows `OK to disconnect` in black and white:**
> 
> This is normal for custom iPod nano firmware. If your iPod restarts or the battery dies, it boots into **disk mode** showing `OK to disconnect` in black and white.  
> ➡️ *This is expected behavior because the custom firmware swaps between the regular OS and disk mode to work properly.*
> ---
> ### **For `iPod nano 7th generation`:**
> 
> 1. Press and hold **`Home`** + **`Power`** until the **Apple logo** appears.  
> 2. Once you see the Apple logo, **release both buttons immediately**.  
> 3. Then, quickly press and hold **`Volume Up`** + **`Volume Down`** until the **Home Screen** shows up.
> ---
> ### **For `iPod nano 6th generation`:**
> 
> 1. Press and hold **`Volume Down`** + **`Power`** until the **Apple logo** appears.  
> 2. Once you see the Apple logo, **release the `Power` button**.  
> 3. Then, quickly press and hold **`Volume Down`** + **`Volume Up`** until the **Home Screen** appears.
"""

REPLY_THEME = """
> ### 🎨 **How to Create a Theme for iPod Nano 6G / 7G**
> **Step 1:** Go to Zeehondie's [Nano Asset Replacer](https://nano.zeehondie.net/asset-replacer-ui/client/)  
> **Step 2:** Choose the Nano you want to create a theme for (**N6G**/**N7G**)  
> **Step 3:** Import the `.IPSW` you want to use as a base *(Get it from [NanoVault](https://github.com/g0lder/NanoVault/tree/main/) or from #share-your-themes)*  
> **Step 4 (VERY IMPORTANT):** Click **Copy All From Origin**  
> **Step 5:** Choose either *Show some Assets* or *Choose all Asset*  
> **Step 6:** Replace the assets  
> **Step 7:** Scroll to the bottom and **generate the custom IPSW** *(Choose either or BOTH from 2012 IPSW / 2015 IPSW if you have a N7G)*  
> **Step 8:** Wait and **profit** 🎉
"""

async def update_status():
    custom_status = load_custom_status()
    user_status_text = load_user_status()
    # Activity (multiline for counter + version/custom)
    state_lines = [f"Solved Cases: {solved_count} | {user_status_text}"]
    if custom_status:
        state_lines.append(custom_status)
    else:
        state_lines.append(f"Ver: {version}")
    state = "\n".join(state_lines)
    activity = discord.Activity(type=discord.ActivityType.playing, name=state)
    status_map = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd,
        "invisible": discord.Status.invisible
    }
    # If user_status_text is a known status, use it, else default to online
    presence_status = status_map.get(user_status_text.lower(), discord.Status.online)
    await client.change_presence(status=presence_status, activity=activity)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    await update_status()

def is_bot_enabled():
    # Always check the flag file, do not cache
    return load_bot_enabled()

@client.event
async def on_message(message):
    global solved_count

    if message.author.bot:
        return

    if not is_bot_enabled():
        return

    content = message.content.lower()

    # OK to disconnect detection
    if pattern_disconnect.search(content):
        solved_count += 1
        save_solved_count(solved_count)
        await update_status()
        try:
            await message.author.send(REPLY_DISCONNECT)
            await message.channel.send(f"{message.author.mention} I've sent you the tutorial to exit the Disk Mode screen in DMs 📩👌")
        except discord.Forbidden:
            await message.channel.send(f"{message.author.mention} I can't DM you — please enable DMs.")
        return

    # Theme creation detection
    if pattern_theme.search(content):
        solved_count += 1
        save_solved_count(solved_count)
        await update_status()
        try:
            await message.author.send(REPLY_THEME)
            await message.channel.send(f"{message.author.mention} I've sent you the tutorial to create a theme in DMs 🎨📩👌")
        except discord.Forbidden:
            await message.channel.send(f"{message.author.mention} I can't DM you — please enable DMs.")
        return

# --- Bot control functions for dashboard ---

def get_bot_status():
    return {
        "enabled": is_bot_enabled(),
        "solved_count": solved_count,
        "custom_status": load_custom_status(),
        "user_status": load_user_status(),
        "username": str(client.user) if client.user else None
    }

def set_solved_count(new_count):
    global solved_count
    solved_count = new_count
    save_solved_count(solved_count)

def set_custom_status(new_status):
    save_custom_status(new_status)

def set_user_status(new_status):
    save_user_status(new_status)

def restart_bot():
    os.execv(__file__, ['python'] + sys.argv)

def shutdown_bot():
    os._exit(0)

# --- Expose control functions to control_panel ---

def dashboard_set_enabled(enabled: bool):
    set_bot_enabled(enabled)
    # No need to cache, always read from file

def dashboard_set_solved_count(new_count: int):
    set_solved_count(new_count)
    # Update status immediately
    coro = update_status()
    try:
        import asyncio
        asyncio.run_coroutine_threadsafe(coro, client.loop)
    except Exception:
        pass

def dashboard_set_custom_status(new_status: str):
    set_custom_status(new_status)
    # Update status immediately
    coro = update_status()
    try:
        import asyncio
        asyncio.run_coroutine_threadsafe(coro, client.loop)
    except Exception:
        pass

def dashboard_set_user_status(new_status: str):
    set_user_status(new_status)
    # Update status immediately
    coro = update_status()
    try:
        import asyncio
        asyncio.run_coroutine_threadsafe(coro, client.loop)
    except Exception:
        pass

def dashboard_restart():
    restart_bot()

def dashboard_shutdown():
    shutdown_bot()

# --- Start Flask control panel in a separate thread ---
if __name__ == "__main__":
    from control_panel import start_control_panel
    threading.Thread(target=start_control_panel, daemon=True).start()
    client.run(TOKEN)
