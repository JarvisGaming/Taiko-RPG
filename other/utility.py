import datetime

import aiosqlite
import dotenv
from classes.exp_bar import ExpBar
from data.channel_list import APPROVED_CHANNEL_ID_LIST
from discord import app_commands
from discord.ext import commands, tasks
from other.global_constants import *


@tasks.loop(hours=3)
async def regularly_clean_score_database():
    """Removes outdated scores from the score database at regular intervals. Active when bot starts."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        # Deletes scores older than 24 hours
        await conn.execute("DELETE FROM submitted_scores WHERE timestamp <= datetime('now', '-24 hours')")
        await conn.commit()

@tasks.loop(hours=12)
async def regularly_refresh_access_token():
    """
    The access token expires every 24 hours.
    https://osu.ppy.sh/docs/index.html#using-the-access-token-to-access-the-api
    """

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
    
    async with http_session.conn.post("https://osu.ppy.sh/oauth/token", headers=headers, data=data) as resp:
        json_file = await resp.json()
        os.environ["OSU_API_ACCESS_TOKEN"] = json_file['access_token']  # Updates local environment variable
        dotenv.set_key(dotenv_path="./data/sensitive.env", key_to_set="OSU_API_ACCESS_TOKEN", value_to_set=json_file['access_token'])  # Global
        print(f"{datetime.datetime.now()}: Access token refreshed")

@tasks.loop(hours=1)
async def regularly_backup_database():
    google_auth.Refresh()  # Refreshes access token, which expires after 1 hour

    TAIKO_RPG_FOLDER_ID = "1UIregYRQZzmNmPcJdwJBtK9Y7N187fDh"
    current_datetime = datetime.datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    metadata = {
        'parents': [
            {"id": TAIKO_RPG_FOLDER_ID}
        ],
        'title': f"{current_datetime}.db",
        'mimeType': "multipart/form-data"
    }
    file = google_drive.CreateFile(metadata=metadata)
    file.SetContentFile("./data/database.db")
    file.Upload()

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

async def send_in_all_channels(message: str):
    """Sends <message> in all approved channels."""
    
    for channel_id in APPROVED_CHANNEL_ID_LIST:
        channel = bot.get_channel(channel_id)
        await channel.send(message)  # type: ignore
        
def create_str_of_allowed_mods() -> str:
    """Creates a string listing all currently accepted mods."""
    
    new_message = ""
    
    # Adds all allowed mods to the message
    for mod in ALLOWED_MODS:
        new_message += f"{mod} "
    
    return new_message.strip()  # Removes trailing space

async def user_is_in_database(osu_id: int | None = None, discord_id: int | None = None, osu_username: str | None = None) -> bool:
    """Checks if user is in the database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        # Tries to find the user in the database
        if osu_id is not None:
            await cursor.execute("SELECT 1 FROM exp_table WHERE osu_id=?", (osu_id,))
        
        elif discord_id is not None:
            await cursor.execute("SELECT 1 FROM exp_table WHERE discord_id=?", (discord_id,))
            
        elif osu_username is not None:
            await cursor.execute("SELECT 1 FROM exp_table WHERE osu_username=?", (osu_username,))
        
        return await cursor.fetchone() is not None

async def get_osu_id(discord_id: int | None = None, osu_username: str | None = None) -> int | None:
    """Returns None if not found in database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        if discord_id is not None:
            await cursor.execute("SELECT osu_id FROM exp_table WHERE discord_id=?", (discord_id,))
            
        elif osu_username is not None:
            await cursor.execute("SELECT osu_id FROM exp_table WHERE osu_username=?", (osu_username,))
        
        data = await cursor.fetchone()
        if data is not None:
            return data[0]
        return None

async def get_discord_id(osu_id: int | None = None, osu_username: str | None = None) -> int | None:
    """Returns None if not found in database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        if osu_id is not None:
            await cursor.execute("SELECT discord_id FROM exp_table WHERE osu_id=?", (osu_id,))
        
        elif osu_username is not None:
            await cursor.execute("SELECT discord_id FROM exp_table WHERE osu_username=?", (osu_username,))
        
        data = await cursor.fetchone()
        if data is not None:
            return data[0]
        return None

async def get_osu_username(discord_id: int | None = None, osu_id: int | None = None) -> str | None:
    """Returns None if not found in database."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        if discord_id is not None:
            await cursor.execute("SELECT osu_username FROM exp_table WHERE discord_id=?", (discord_id,))
        
        elif osu_id is not None:
            await cursor.execute("SELECT osu_username FROM exp_table WHERE osu_id=?", (osu_id,))
        
        data = await cursor.fetchone()
        if data is not None:
            return data[0]
        return None
 
async def get_user_exp_bars(discord_id: int | None = None, osu_id: int | None = None, osu_username: str | None = None) -> dict[str, ExpBar]:
    
    user_exp_bars = {}
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        for exp_bar_name in EXP_BAR_NAMES:
            
            if discord_id is not None:
                await cursor.execute(f"SELECT {exp_bar_name.lower()}_exp FROM exp_table WHERE discord_id=?", (discord_id,))
            elif osu_id is not None:
                await cursor.execute(f"SELECT {exp_bar_name.lower()}_exp FROM exp_table WHERE osu_id=?", (osu_id,))
            elif osu_username is not None:
                await cursor.execute(f"SELECT {exp_bar_name.lower()}_exp FROM exp_table WHERE osu_username=?", (osu_username,))
            
            data = await cursor.fetchone()
            
            assert data is not None
            total_exp = data[0]
            
            exp_bar = ExpBar(total_exp)
            user_exp_bars[exp_bar_name] = exp_bar
    
    return user_exp_bars

async def get_user_currency(discord_id: int | None = None, osu_id: int | None = None, osu_username: str | None = None) -> dict[str, int]:
    
    if discord_id is not None:
        osu_id = await get_osu_id(discord_id=discord_id)
    elif osu_username is not None:
        osu_id = await get_osu_id(osu_username=osu_username)
    
    async with aiosqlite.connect("./data/database.db") as conn:
        conn.row_factory = aiosqlite.Row  # Allows the query to return a dict-like
        cursor = await conn.execute("SELECT * FROM currency WHERE osu_id=?", (osu_id,))
        row = await cursor.fetchone()
        assert row is not None
        
    user_currency: dict[str, int] = {}
    for currency_name in row.keys():
        if currency_name == 'osu_id': continue  # Not a currency
        user_currency[currency_name] = row[currency_name]

    return user_currency

def create_str_of_user_currency(user_currency: dict[str, int]) -> str:
    output = ""
    for currency_id, currency_amount in user_currency.items():
        output += f"{currency_amount} {ANIMATED_CURRENCY_UNIT_EMOJIS[currency_id]}  "
    return output

def prettify_currency_db_name(currency_name: str) -> str:
    pretty_currency_name = {
        'taiko_tokens': "Taiko Tokens"
    }
    return pretty_currency_name[currency_name]

async def get_user_upgrades(discord_id: int | None = None, osu_id: int | None = None, osu_username: str | None = None) -> dict[str, int]:
    if discord_id is not None:
        osu_id = await get_osu_id(discord_id=discord_id)
    elif osu_username is not None:
        osu_id = await get_osu_id(osu_username=osu_username)
    
    async with aiosqlite.connect("./data/database.db") as conn:
        conn.row_factory = aiosqlite.Row  # Allows the query to return a dict-like
        cursor = await conn.execute("SELECT * FROM upgrades WHERE osu_id=?", (osu_id,))
        row = await cursor.fetchone()
        assert row is not None

    user_upgrades: dict[str, int] = {}
    for upgrade_name in row.keys():
        if upgrade_name == 'osu_id': continue  # Not an upgrade
        user_upgrades[upgrade_name] = row[upgrade_name]

    return user_upgrades

