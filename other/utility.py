import aiosqlite
import dotenv
from classes.exp_bar import ExpBar
from data.channel_list import APPROVED_CHANNEL_ID_LIST
from discord import app_commands
from discord.ext import commands, tasks
from other.global_constants import *


@tasks.loop(hours=1)
async def regularly_clean_replay_database():
    """Removes outdated replays from the replay database at regular intervals. Active when bot starts."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        # Deletes replays older than 24 hours
        await cursor.execute("DELETE FROM submitted_replays WHERE timestamp <= datetime('now', '-24 hours')")
        await conn.commit()

@tasks.loop(hours=6)
async def regularly_refresh_access_token():
    """https://osu.ppy.sh/docs/index.html#using-the-access-token-to-access-the-api"""

    headers = {
        'Accept': "application/json",
        'Content-Type': "application/x-www-form-urlencoded",
    }
    data = {
        'client_id': OSU_CLIENT_ID,
        'client_secret': OSU_CLIENT_SECRET,
        'grant_type': "client_credentials",
        'scope': "public",
    }
    
    http_session = aiohttp.ClientSession()
    
    async with http_session.post("https://osu.ppy.sh/oauth/token", headers=headers, data=data) as resp:
        json_file = await resp.json()
        dotenv.set_key(dotenv_path="./data/sensitive.env", key_to_set="OSU_API_ACCESS_TOKEN", value_to_set=json_file['access_token'])
        
    await http_session.close()

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
    for mod in ALLOWED_MODS:
        new_message += f"{mod} "
    
    return new_message.strip()  # Removes trailing space

async def get_osu_id_from_discord_id(discord_id: int) -> int | None:
    """Returns None if not found in database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        await cursor.execute("SELECT osu_id FROM exp_table WHERE discord_id=?", (discord_id,))
        data = await cursor.fetchone()
        
        if data is not None:
            return data[0]
        return None

async def get_discord_id_from_osu_id(osu_id: int) -> int | None:
    """Returns None if not found in database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        await cursor.execute("SELECT discord_id FROM exp_table WHERE osu_id=?", (osu_id,))
        data = await cursor.fetchone()
        
        if data is not None:
            return data[0]
        return None
    
async def get_user_exp_bars(discord_id: int) -> dict[str, ExpBar]:
    
    user_exp_bars = {}
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        for exp_bar_name in EXP_BAR_NAMES:
            await cursor.execute(f"SELECT {exp_bar_name.lower()}_exp FROM exp_table WHERE discord_id=?", (discord_id,))
            data = await cursor.fetchone()
            
            assert data is not None
            total_exp = data[0]
            
            exp_bar = ExpBar(total_exp)
            user_exp_bars[exp_bar_name] = exp_bar
    
    return user_exp_bars