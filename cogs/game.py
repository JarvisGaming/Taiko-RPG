import discord
from discord import app_commands

import osrparse
import ossapi
import datetime
import math
import uuid  # Generate random file names
import re
import datetime
from discord.ext import commands

from other.global_constants import *
from other.utility import *

async def user_is_not_verified(conn: aiosqlite.Connection, channel: discord.abc.Messageable, discord_id: int) -> bool:
    """Checks if user is NOT verified. Return True if yes, False otherwise."""
    
    cursor = await conn.cursor()
    
    # Fetch the row with the user's discord id
    await cursor.execute("SELECT 1 FROM exp_table WHERE discord_id=?", (discord_id,))
    data = await cursor.fetchone()
    
    # If we can't find anything, that means the user is not verified
    if data is None:
        await channel.send("You are not verified. Do `/verify <profile link>` to get started!")
        return True
    return False

def determine_mods_used(replay: osrparse.Replay) -> dict[str, bool]:
    """Given a replay, return a dict with mods as the keys, and bool values to indicate whether they are turned on."""
    
    # Replay mods are stored as a bit string
    replay_mods = int(replay.mods)
            
    mods_used: dict[str, bool] = {
        # Every mod other than these are irrelevant for taiko
        
        'NM': replay_mods == 0,  # A replay is NoMod when no other mods are on
        'NF': bool(replay_mods & (1 << 0)),
        'EZ': bool(replay_mods & (1 << 1)),
        'TD': bool(replay_mods & (1 << 2)),
        'HD': bool(replay_mods & (1 << 3)),
        'HR': bool(replay_mods & (1 << 4)),
        'SD': bool(replay_mods & (1 << 5)),
        'DT': bool(replay_mods & (1 << 6)),
        'RX': bool(replay_mods & (1 << 7)),
        'HT': bool(replay_mods & (1 << 8)),
        'NC': bool(replay_mods & (1 << 9)),  # If this is on, DT is also on
        'FL': bool(replay_mods & (1 << 10)),
        'Auto': bool(replay_mods & (1 << 11)),
        'SO': bool(replay_mods & (1 << 12)),
        'AP': bool(replay_mods & (1 << 13)),
        'PF': bool(replay_mods & (1 << 14)),  # If this is on, SD is also on
        "ScoreV2": bool(replay_mods & (1 << 29))
    }
    
    return mods_used

async def replay_has_illegal_mods(channel: discord.abc.Messageable, mods_used: dict[str, bool]) -> bool:
    """Check if replay uses a mod that is unsupported. Return True if yes, False otherwise."""
    
    # Cycle through all entries in the mods_used dict
    for mod, value in mods_used.items():
        
        # No need to do anything if the replay uses a mod that's accepted
        if mod in ACCEPTED_MODS:
            continue
        
        # If it's not an accepted mod, we'll check whether it's turned on
        if value == True:
            
            # If it's turned on, we'll send a message
            new_message = "Only the following mods are supported: "
            new_message += create_str_of_accepted_mods()
                
            await channel.send(new_message)
            return True
    
    return False

async def replay_is_not_taiko(channel: discord.abc.Messageable, replay: osrparse.Replay) -> bool:
    """Check if replay is NOT a taiko replay. Return True if yes, False otherwise."""
    
    if replay.mode != osrparse.GameMode.TAIKO:
        await channel.send("This isn't a taiko replay!")
        return True
    return False

async def replay_is_a_convert(channel: discord.abc.Messageable, beatmap: ossapi.Beatmap) -> bool:
    """Check if replay is a convert. Return True if yes, False otherwise."""
    
    if beatmap.mode != ossapi.GameMode.TAIKO:
        await channel.send("This is a convert replay!")
        return True
    return False

async def replay_is_outdated(channel: discord.abc.Messageable, replay: osrparse.Replay) -> bool:
    """Check if replay was made in the last 24 hours. Return True if yes, False otherwise."""
    
    time_difference = datetime.datetime.now(datetime.timezone.utc) - replay.timestamp  # now() doesn't have timezone info, so we need to add it
    one_day = datetime.timedelta(days=1)
    
    if time_difference >= one_day:
        await channel.send("Replay must be made within the last 24 hours!")
        return True
    return False

async def replay_not_made_by_user(conn: aiosqlite.Connection, channel: discord.abc.Messageable, osu_id_in_replay: int, discord_id: int) -> bool:
    """Check if replay was NOT made by user. Return True if yes, False otherwise."""
 
    cursor = await conn.cursor()
 
    # Retrieve the user's osu id using their discord id
    await cursor.execute("SELECT osu_id FROM exp_table WHERE discord_id=?", (discord_id,))
    data = await cursor.fetchone()
    
    assert data is not None
    osu_id_in_database = data[0]

    # If user's osu id in the database is different than that in the replay, that means it's not made by the user
    if osu_id_in_database != osu_id_in_replay:
        await channel.send("This replay is not yours!")
        return True
    return False

async def replay_already_submitted(conn: aiosqlite.Connection, channel: discord.abc.Messageable, osu_id: int, 
                                   beatmap: ossapi.Beatmap, beatmapset: ossapi.Beatmapset, replay: osrparse.Replay) -> bool:
    """Check if replay has already been submitted by the user (ie in the replay database). Return True if yes, False otherwise."""
    
    cursor = await conn.cursor()
    
    # See if the replay database contains a row with the exact same information as the submitted replay
    query = "SELECT * FROM submitted_replays WHERE osu_id=? AND beatmap_id=? AND beatmapset_id=? AND timestamp=?"
    await cursor.execute(query, (osu_id, beatmap.id, beatmapset.id, replay.timestamp))
    data = await cursor.fetchone()
    
    # If there is, that means the replay has already been submitted
    if data is not None:
        await channel.send("You already submitted this replay!")
        return True
    return False

def calculate_total_exp_gained(replay: osrparse.Replay, beatmap: ossapi.Beatmap) -> int:
    """Calculate the TOTAL exp gained from submitting a replay based on a formula."""
    
    total_exp_gained = math.pow(max(3*replay.count_300 + 0.75*replay.count_100 - 3*replay.count_miss, 0), 0.6) * math.pow(beatmap.difficulty_rating+1, 1.2) * 0.05
    total_exp_gained = int(total_exp_gained)
    return total_exp_gained

def create_exp_dict() -> dict[str, int]:
    """Returns a dict with all relevant mods (mods with their own exp, including the overall exp) as keys, with their values set to 0."""
    
    # Initialize it with the overall exp data
    exp_dict = {'Overall': 0} 
    
    # Add all relevant mods to the dict
    for mod in RELEVANT_MODS:
        exp_dict[mod] = 0
    
    return exp_dict
    
def calculate_mod_exp_gained(total_exp_gained: int, exp_gained: dict[str, int], mods_used: dict[str, bool]):
    """
    Calculate the exp gained for each mod. If there are no mods, only NoMod exp will be given.
    Otherwise, split exp amongst activated relevant mods (mods with their own exp bars).
    exp_gained contains the amount of exp gained for each mod.
    """
    
    # Update the overall exp gained in the exp_gained dict
    exp_gained['Overall'] = total_exp_gained
    
    # If no mods are active, allocate all exp gained to NoMod
    if mods_used['NM'] == True:
        exp_gained['NM'] = total_exp_gained
        return
    
    # Otherwise, count the number of relevant mods activated
    num_mods_activated: int = 0
    
    # Loop through all relevant mods
    for mod in RELEVANT_MODS:
        
        # If a relevant mod is activated, increment the count
        if mods_used[mod] == True:
            num_mods_activated += 1
    
    # Loop through all relevant mods again
    for mod in RELEVANT_MODS:
        
        # Calculate the exp gained for each mod
        if mods_used[mod] == True:
            exp_gained[mod] = total_exp_gained // num_mods_activated
            
def calculate_level_information(total_exp: int, return_level_only: bool = False) -> int | tuple[int, int, int]:
    """
    Given the total exp for a particular mod, calculate and return the level, progress towards the next level, and the exp required for the next level.
    If <return_level_only> is True, only return the level.
    
    Current formula:
    You start at level 1 with 0 xp. Level 2 requires 50 exp. Level 3 requires 100 MORE exp. And so on.
    """

    level = 1
    exp_required = 50   # EXP required for the next level
    
    # From the total exp, deduct the exp required for each subsequent level
    while total_exp >= exp_required:
        level += 1
        total_exp -= exp_required
        exp_required += 50
        
    progress_to_next_lv = total_exp  # Renamed for clarity
    
    if return_level_only == True:
        return level
    return level, progress_to_next_lv, exp_required            

async def update_user_exp_and_levels(conn: aiosqlite.Connection, osu_id: int, exp_gained: dict[str, int]):
    """Update user's exp in the database."""
    
    cursor = await conn.cursor()
    
    # Get the user's exp data using their osu id
    await cursor.execute("SELECT overall_exp, nm_exp, hd_exp, hr_exp FROM exp_table WHERE osu_id=?", (osu_id,))
    data = await cursor.fetchone()

    # Calculate the new exp values
    assert data is not None
    new_overall_exp = data[0] + exp_gained['Overall']
    new_nm_exp = data[1] + exp_gained['NM']
    new_hd_exp = data[2] + exp_gained['HD']
    new_hr_exp = data[3] + exp_gained['HR']
    
    new_overall_level = calculate_level_information(new_overall_exp, return_level_only=True)
    new_nm_level = calculate_level_information(new_nm_exp, return_level_only=True)
    new_hd_level = calculate_level_information(new_hd_exp, return_level_only=True)
    new_hr_level = calculate_level_information(new_hr_exp, return_level_only=True)
    
    # Update the exp values in the database
    query = "UPDATE exp_table SET overall_exp=?, nm_exp=?, hd_exp=?, hr_exp=? WHERE osu_id=?"
    await cursor.execute(query, (new_overall_exp, new_nm_exp, new_hd_exp, new_hr_exp, osu_id))
    
    # Update the user's levels
    query = "UPDATE exp_table SET overall_level=?, nm_level=?, hd_level=?, hr_level=? WHERE osu_id=?"
    await cursor.execute(query, (new_overall_level, new_nm_level, new_hd_level, new_hr_level, osu_id))

def calculate_accuracy(replay: osrparse.Replay) -> float:
    """Helper function for add_replay_stats. Calculate accuracy according to https://osu.ppy.sh/wiki/en/Gameplay/Accuracy"""
    
    accuracy = replay.count_300 + 0.5*replay.count_100
    accuracy /= replay.count_300 + replay.count_100 + replay.count_miss
    accuracy *= 100
    return accuracy

def get_mod_list(mods_used: dict[str, bool]) -> str:
    """Helper function for add_replay_stats. Given a dict of mods used, return a string of all active mods."""

    # Gets the mods used in the replay
    mod_list: str = ""

    # Loop through all possible mods
    for key, value in mods_used.items():
        
        # If that mod is not active, ignore it
        if value == False:
            continue
        
        # If the mod is active AND it's NoMod, then NoMod is the only thing active
        if key == 'NM':
            mod_list = "NoMod"
            break
        
        # If SD is active AND PF is active, don't display SD
        if key == 'SD' and mods_used['PF'] == True:
            continue
        
        # If DT is active AND NC is active, don't display DT
        if key == 'DT' and mods_used['NC'] == True:
            continue
        
        # Otherwise just add the active mod to the list
        mod_list += (f"{key} ")
    
    return mod_list.strip()  # Removes trailing space

async def add_replay_stats(embed: discord.Embed, beatmap: ossapi.Beatmap, beatmapset: ossapi.Beatmapset, 
                           replay: osrparse.Replay, mods_used: dict[str, bool]):
    """Add different statistics about the replay to an embed.""" 
    
    mod_list = get_mod_list(mods_used)
    accuracy = calculate_accuracy(replay)
    
    # Add the replay stats to the embed
    embed.title = f"Your replay has been submitted!"
    metadata: str = f"{beatmapset.artist} - {beatmapset.title} [{beatmap.version}]"
    stats: str = f"{beatmap.difficulty_rating:.2f}* ▸ {accuracy:.2f}% ▸ `[{replay.count_300} • {replay.count_100} • {replay.count_miss}]` ▸ {mod_list}"
    
    embed.add_field(name=metadata, value=stats, inline=False)

async def add_updated_user_exp(conn: aiosqlite.Connection, embed: discord.Embed, osu_id: int, exp_gained: dict[str, int]):
    """Add user's updated exp values to the embed. Mods whose exp have no update aren't displayed."""
    
    cursor = await conn.cursor()
    
    # Get all of user's exp values from the database
    await cursor.execute("SELECT overall_exp, nm_exp, hd_exp, hr_exp FROM exp_table WHERE osu_id=?", (osu_id,))
    data = await cursor.fetchone()
    
    # Create a dict with the total amount of exp for each mod
    assert data is not None
    total_exp: dict[str, int] = {
        'Overall': data[0],
        'NM': data[1],
        'HD': data[2],
        'HR': data[3],
    }
    
    # Loop through all mods that have their own exp, in addition to the overall exp
    for mod_name in (['Overall'] + RELEVANT_MODS):
        
        # Only display the mod exp if you gained exp for it
        if exp_gained[mod_name] != 0:
            level, progress_to_next_lv, exp_required = calculate_level_information(total_exp[mod_name])  # type: ignore
            
            # Add mod exp information to the embed
            name = f"{mod_name} Level {level}:\n"
            value = f"{progress_to_next_lv} / {exp_required} **(+{exp_gained[mod_name]})**\n"  # [Progress to next level in exp / Required exp for next level]
            embed.add_field(name=name, value=value)
            
async def add_replay_to_database(conn: aiosqlite.Connection, osu_id: int, beatmap: ossapi.Beatmap, beatmapset: ossapi.Beatmapset, replay: osrparse.Replay):
    """Add submitted replay to the replay database."""
    
    cursor = await conn.cursor()
    
    # Add the replay
    query = "INSERT INTO submitted_replays VALUES (?, ?, ?, ?)"
    await cursor.execute(query, (osu_id, beatmap.id, beatmapset.id, replay.timestamp))

class GameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener(name="on_message")
    async def submit(self, message: discord.Message):
        """When replay file is posted, give the user the appropriate amount of EXP and display it."""
        
        channel = message.channel
        discord_id = message.author.id
        
        # Loop through all attachments and parse them individually
        for attachment in message.attachments:
            
            # Record the time it takes to submit one replay
            start_time = datetime.datetime.now()
            
            # Reuse the same connection for the same replay
            async with aiosqlite.connect("./data/database.db") as conn:
            
                # Exit immediately if user is not verified
                if await user_is_not_verified(conn, channel, discord_id):
                    break
                
                # Skip attachment if it's not a replay (doesn't contain ".osr" at the end)
                # https://regex-vis.com/?r=.*%3F%5C.osr
                if re.match(r".*?\.osr", attachment.filename) is None:
                    continue
                
                # Replays shouldn't be larger than 1MB, a full run-through of The Unforgiving is about ~800KB
                # Also prevents people from spamming big files to kill my PC
                if attachment.size > 1000000:
                    await channel.send("Size of attachment is too large.")
                    continue
                
                # Save file locally for parsing
                pathname: str = f"./data/replay_{uuid.uuid4()}"  # Randomize pathname
                
                try:
                    await attachment.save(pathname)  # type: ignore
                except Exception as error:
                    await channel.send(f"Failed to save replay as file: {error}")
                    continue
                
                # Parse the file with osrparse
                try:
                    file = open(pathname, "rb")  # Replay must be read in binary
                    replay = osrparse.Replay.from_file(file)
                    file.close()
                    os.remove(pathname)  # Delete the file
                except Exception as error:
                    file.close()         # Repeated, otherwise file won't be deleted
                    os.remove(pathname)  # Repeated, otherwise file won't be deleted
                    await channel.send(f"Failed to parse replay: {error}")
                    continue
                
                # Retrieve beatmap information
                hash = replay.beatmap_hash
                try:
                    beatmap = await osu_api.beatmap(checksum=hash)
                    beatmapset = await osu_api.beatmapset(beatmap_id=beatmap.id)
                except:
                    await channel.send("Map is not submitted!")
                    continue
                    
                # Retrieve user information
                try:
                    user = await osu_api.user(user=replay.username)
                except:
                    await channel.send("Can't find user!")
                    continue
                osu_id = user.id
                
                # Get mods used: https://kszlim.github.io/osu-replay-parser/_modules/osrparse/utils.html#Mod
                # Mods are stored as a bit string
                mods_used = determine_mods_used(replay)
                
                # Skip replay if the replay includes a non-accepted mod
                if await replay_has_illegal_mods(channel, mods_used):
                    continue
                
                # Skip replay if the gamemode isn't taiko
                if await replay_is_not_taiko(channel, replay):
                    continue
                
                # Skip replay if it is a convert
                if await replay_is_a_convert(channel, beatmap):
                    continue
                
                # Skip replay if it is outdated
                if await replay_is_outdated(channel, replay):
                    continue
                
                # Skip replay if it's not made by user
                if await replay_not_made_by_user(conn, channel, osu_id, discord_id):
                    continue
                
                # Skip replay if it's already been submitted
                if await replay_already_submitted(conn, channel, osu_id, beatmap, beatmapset, replay):
                    continue

                # Calculate TOTAL exp gained using an arbitrary formula I cooked up while sleepy
                total_exp_gained = calculate_total_exp_gained(replay, beatmap)
                
                # Calculate exp gained for each mod
                # If there is more than one mod active, exp is evenly split between them
                exp_gained = create_exp_dict()
                calculate_mod_exp_gained(total_exp_gained, exp_gained, mods_used)
                
                # Update user's exp and levels in database
                await update_user_exp_and_levels(conn, osu_id, exp_gained)
                
                # Add the replay to the submitted_replays database
                await add_replay_to_database(conn, osu_id, beatmap, beatmapset, replay)
                
                # Initialize the embed to be sent
                embed = discord.Embed()
                
                # Add stats about the replay to the embed
                await add_replay_stats(embed, beatmap, beatmapset, replay, mods_used)
                
                # Add the user's updated exp stats to the embed
                await add_updated_user_exp(conn, embed, osu_id, exp_gained)
                
                # Commit all database changes
                await conn.commit()
                
                # Calculate the time it took to process the replay and add it to the embed
                time_taken = datetime.datetime.now() - start_time
                seconds = time_taken.seconds
                milliseconds = time_taken.microseconds // 1000
                embed.set_footer(text=f"Time taken: {seconds}.{milliseconds}s")
                
                # Send the embed
                await channel.send(embed=embed)

    @app_commands.command(name="profile", description="Display all of a user's exp information")
    @app_commands.describe(username="The player that you want to see the profile of (case sensitive). Leave blank to see your own.")
    @is_verified()
    async def profile(self, interaction: discord.Interaction, username: str | None = None):
        """Display all of the user's exp information."""
        
        async with aiosqlite.connect("./data/database.db") as conn:
            cursor = await conn.cursor()
            
            # Fetch user's osu username if not provided
            if username is None:
                await cursor.execute("SELECT osu_username FROM exp_table WHERE discord_id=?", (interaction.user.id,))
                data = await cursor.fetchone()
                assert data is not None
                username = data[0]
            
            # Otherwise, check if the user exists in the database
            else:
                await cursor.execute("SELECT 1 FROM exp_table WHERE osu_username=?", (username,))
                data = await cursor.fetchone()
                if data is None:
                    await interaction.response.send_message("User not found!")
                    return
                
            # Fetch user's exp in each mod
            await cursor.execute("SELECT overall_exp, nm_exp, hd_exp, hr_exp FROM exp_table WHERE osu_username=?", (username,))
            data = await cursor.fetchone()
            
            total_exp = create_exp_dict()
        
            assert data is not None
            total_exp['Overall'] = data[0]
            total_exp['NM'] = data[1]
            total_exp['HD'] = data[2]
            total_exp['HR'] = data[3]
        
            # Fetch user's level in each mod
            await cursor.execute("SELECT overall_level, nm_level, hd_level, hr_level FROM exp_table WHERE osu_username=?", (username,))
            data = await cursor.fetchone()
            
            level = create_exp_dict()
            
            assert data is not None
            level['Overall'] = data[0]
            level['NM'] = data[1]
            level['HD'] = data[2]
            level['HR'] = data[3]
        
        # Initialize embed
        embed = discord.Embed(title=f"{username}'s EXP Stats", colour=discord.Colour.blurple())
        
        # Display user's mod exp by looping through all mods
        for mod_name in (["Overall"] + RELEVANT_MODS):  # Combine the "Overall" word with the relevant mods list
            
            # Calculate relevant display information
            level, progress_to_next_lv, exp_required = calculate_level_information(total_exp[mod_name])  # type: ignore
            progress_in_percentage: float = (progress_to_next_lv / exp_required) * 100
            
            # Add exp information for that mod to the embed
            name_info = f"{mod_name} Level {level}:\n"
            value_info = f"{progress_to_next_lv} / {exp_required} ({progress_in_percentage:.2f}%)\n"  # Progress to next level in exp / Required exp for next level
            
            # We want the overall exp to be in its own separate line
            if mod_name == "Overall":
                embed.add_field(name=name_info, value=value_info, inline=False)
            else:
                embed.add_field(name=name_info, value=value_info)
                                
        # Display exp
        await interaction.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(GameCog(bot))