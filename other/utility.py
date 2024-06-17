import datetime
import aiosqlite
from contextlib import closing
from discord.ext import commands, tasks
from discord import app_commands

from other.global_constants import *
from data.channel_list import APPROVED_CHANNEL_ID_LIST

@tasks.loop(hours=1)
async def regularly_clean_replay_database():
    """Removes outdated replays from the replay database at regular intervals. Active when bot starts."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        # Deletes replays older than 24 hours
        await cursor.execute("DELETE FROM submitted_replays WHERE timestamp <= datetime('now', '-24 hours')")
        await conn.commit()

def is_admin():
    """
    Decorator. Checks if user is an admin.
    If user isn't an admin, sends a message and returns False. Returns True otherwise.
    All admin commands are text commands, so we use commands and not app_commands.
    """
    
    async def predicate(ctx: commands.Context):
        """The check in question."""

        if ctx.author.id not in ADMIN_ID_LIST:
            await ctx.send("You're not an admin!")
            return False
        return True
    
    # Adds the check
    return commands.check(predicate)

def is_verified():
    """
    Decorator. Checks if user is verified.
    If user isn't an admin, sends a message and returns False. Returns True otherwise.
    """

    async def predicate(interaction: discord.Interaction):
        """The check in question."""

        async with aiosqlite.connect("./data/database.db") as conn:
            cursor = await conn.cursor()
            
            # Tries to find the user in the database
            await cursor.execute("SELECT 1 FROM exp_table WHERE discord_id=?", (interaction.user.id,))
            user = await cursor.fetchone()

        # If the user isn't in the database, they aren't verified
        if user is None:
            await interaction.response.send_message("You aren't verified yet. Do /verify <profile link> to get started!")
            return False
        return True
    
    # Adds the check
    return app_commands.check(predicate)
    
@bot.event
async def on_command_error(ctx: commands.Context, error):
    """
    Generic error handler for all text commands.
    Note that both command-specific and cog-specific error handlers are called before this generic handler.
    """
    
    await ctx.send(f"An exception occurred: {error}")

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error):
    """
    Generic error handler for all slash commands.
    Note that both command-specific and cog-specific error handlers are called before this generic handler.
    """
    
    await interaction.response.send_message(f"An exception occurred: {error}")

async def send_in_all_channels(message: str):
    """Sends <message> in all approved channels."""
    
    for channel_id in APPROVED_CHANNEL_ID_LIST:
        channel = bot.get_channel(channel_id)
        await channel.send(message)  # type: ignore
        
def create_str_of_allowed_replay_mods() -> str:
    """Creates a string listing all currently accepted mods."""
    
    new_message = ""
    
    # Adds all allowed mods to the message
    for mod in ALLOWED_REPLAY_MODS:
        new_message += f"{mod} "
    
    return new_message.strip()  # Removes trailing space