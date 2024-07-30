import os
import sys

import other.utility
from classes.http_session import http_session
from other.error_handling import *


@bot.event
async def setup_hook():
    """This is run once when the bot starts."""
    
    await load_all_cogs()
    await bot.tree.sync()  # Syncs slash commands
    await http_session.start_http_session()
    
    if not await other.utility.buffs_are_synced_with_database():
        sys.exit(-1)
    
    # Backup only the live database
    if not os.getcwd().endswith("test"):
        other.utility.regularly_backup_database.start()
    
    other.utility.regularly_clean_score_database.start()
    other.utility.regularly_refresh_access_token.start()
    
async def load_all_cogs():
    """Load bot commands stored in the cogs folder."""

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
            except Exception as error:
                await other.utility.send_in_all_channels(f"**Failed to load {filename}: {error}**")
    
@bot.event
async def on_ready():
    """Runs after setup_hook()."""
    
    await other.utility.send_in_all_channels("Bot is now ready")

sys.stderr = open("./logs.log", "w")  # Redirect stderr to log file
bot.run(BOT_TOKEN)