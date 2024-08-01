import datetime
import os
from typing import Optional

import aiosqlite
import dotenv
from classes.currency import Currency, CurrencyID
from classes.exp import ExpBar, ExpBarName
from classes.http_session import http_session
from classes.mod import AllowedMods
from classes.upgrade import upgrade_manager
from data.channel_list import APPROVED_CHANNEL_ID_LIST
from discord import app_commands
from discord.ext import tasks
from other.global_constants import *


@tasks.loop(hours=3)
async def regularly_clean_score_database():
    """Removes outdated scores from the score database at regular intervals. Active when bot starts."""
    
    async with aiosqlite.connect("./data/database.db") as conn:
        # Deletes scores older than 24 hours
        await conn.execute("DELETE FROM submitted_scores WHERE timestamp <= datetime('now', '-24 hours')")
        await conn.commit()

@tasks.loop(hours=12)
async def regularly_refresh_osu_api_access_token():
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
    
    async with http_session.interface.post("https://osu.ppy.sh/oauth/token", headers=headers, data=data) as resp:
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

async def buffs_are_synced_with_database() -> bool:
    """
    Checks if all the buffs in the managers are present in the database. 
    Warns user if the buffs in the code and database don't match.
    """
    
    upgrades_are_synced: bool = True
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        # Checking upgrades
        upgrades_in_code = [upgrade_id for upgrade_id in upgrade_manager.upgrades.keys()]
        
        await cursor.execute("SELECT name FROM pragma_table_info('upgrades') WHERE name != 'osu_id'")
        data = await cursor.fetchall()
        upgrades_in_database = [row[0] for row in data]
            
        if sorted(upgrades_in_code) != sorted(upgrades_in_database):
            upgrades_are_synced = False
    
    if not upgrades_are_synced:
        print("WARNING: Upgrades aren't synced in database!")
        print(f"Outlier in code: {set(upgrades_in_code) - set(upgrades_in_database)}")
        print(f"Outlier in database: {set(upgrades_in_database) - set(upgrades_in_code)}")
    
    return upgrades_are_synced
        
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
        
def command_cooldown_for_live_bot(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
    """Makes certain commands (eg submit) have a cooldown on the live version of the bot, while disabling it for the test version."""
    if os.getcwd().endswith("test"):
        return None
    return app_commands.Cooldown(rate=1, per=300.0)
    
def create_str_of_allowed_mods() -> str:
    """Creates a string listing all currently accepted mods."""
    
    new_message = ""
    
    # Adds all allowed mods to the message
    for mod in AllowedMods.list_as_str():
        new_message += f"{mod} "
    
    return new_message.strip()  # Removes trailing space

async def user_is_in_database(osu_id: Optional[int] = None, discord_id: Optional[int] = None, osu_username: Optional[str] = None) -> bool:
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

async def get_osu_id(discord_id: Optional[int] = None, osu_username: Optional[str] = None) -> Optional[int]:
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

async def get_discord_id(osu_id: Optional[int] = None, osu_username: Optional[str] = None) -> Optional[int]:
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

async def get_osu_username(discord_id: Optional[int] = None, osu_id: Optional[int] = None) -> Optional[str]:
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
 
async def get_user_exp_bars(discord_id: Optional[int] = None, osu_id: Optional[int] = None, osu_username: Optional[str] = None) -> dict[str, ExpBar]:
    
    user_exp_bars = {}
    
    async with aiosqlite.connect("./data/database.db") as conn:
        cursor = await conn.cursor()
        
        for exp_bar_name in ExpBarName.list_as_str():
            
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

async def get_user_currency(discord_id: Optional[int] = None, osu_id: Optional[int] = None, osu_username: Optional[str] = None) -> dict[str, int]:
    
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
        all_currencies = get_all_currencies()
        output += f"{currency_amount} {all_currencies[currency_id].animated_discord_emoji}  "
    return output

def prettify_currency_db_name(currency_name: str) -> str:
    pretty_currency_name = {
        'taiko_tokens': "Taiko Tokens"
    }
    return pretty_currency_name[currency_name]

async def get_user_upgrade_levels(discord_id: Optional[int] = None, osu_id: Optional[int] = None, osu_username: Optional[str] = None) -> dict[str, int]:
    if discord_id is not None:
        osu_id = await get_osu_id(discord_id=discord_id)
    elif osu_username is not None:
        osu_id = await get_osu_id(osu_username=osu_username)
    
    async with aiosqlite.connect("./data/database.db") as conn:
        conn.row_factory = aiosqlite.Row  # Allows the query to return a dict-like
        cursor = await conn.execute("SELECT * FROM upgrades WHERE osu_id=?", (osu_id,))
        row = await cursor.fetchone()
        assert row is not None

    user_upgrade_levels: dict[str, int] = {}
    for upgrade_name in row.keys():
        if upgrade_name == 'osu_id': continue  # Not an upgrade
        user_upgrade_levels[upgrade_name] = row[upgrade_name]

    return user_upgrade_levels

def get_all_currencies() -> dict[str, Currency]:
    """Returns a dict with the currency id as the key, and its Currency object as the value."""
    
    currencies = {}
    currencies['taiko_tokens'] = Currency(
        currency_id = CurrencyID.taiko_tokens,
        discord_emoji = "<:taiko_tokens:1259156904349794357>",
        animated_discord_emoji = "<a:taiko_tokens_spinning:1259859321475305504>",
    )
    
    return currencies