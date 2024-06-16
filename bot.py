import os
import sys
from other.global_constants import *
from other.utility import *

async def load_extensions():
    """Load bot commands and other functions stored in the cogs folder."""

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
            except Exception as error:
                await send_in_all_channels(f"**Failed to load {filename}: {error}**")

@bot.event
async def on_ready():
    """Sets up the bot on startup."""
    
    await send_in_all_channels("Bot is now ready")
    # The bot's activity status is set in the commands.Bot class constructor,
    # as it can cause crashes when put here.

@bot.event
async def setup_hook():
    """This is run once when the bot starts."""
    
    await load_extensions()         # Loads all cogs
    await bot.tree.sync()           # Syncs slash commands
    clean_replay_database.start()   # Starts the looping task to regularly clean replay database


sys.stderr = open("./logs.log", "w")  # Redirect stderr to log file
bot.run(BOT_TOKEN)