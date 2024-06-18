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

async def user_is_verified(conn: aiosqlite.Connection, channel: discord.abc.Messageable, discord_id: int) -> bool:
    """Checks if user is verified. Return True if yes, False otherwise."""
    
    cursor = await conn.cursor()
    
    # Fetch the row with the user's discord id
    await cursor.execute("SELECT 1 FROM exp_table WHERE discord_id=?", (discord_id,))
    user = await cursor.fetchone()
    
    # If we can't find anything, that means the user is not verified
    if user is None:
        await channel.send("You are not verified. Do `/verify <profile link>` to get started!")
        return False
    return True

def determine_mods_used(replay: osrparse.Replay) -> dict[str, bool]:
    """Given a replay, return a dict with mods as the keys, and bool values to indicate whether they are turned on."""
    
    # Replay mods are stored as a bit string
    replay_mods = int(replay.mods)
            
    mods_used: dict[str, bool] = {
        # Every mod other than these are irrelevant for taiko
        
        'NM': True,  # We check whether it's actually the case later, since there are certain mods that we want to count as NoMod
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
    
    # Even if only ScoreV2 / NF / SD / PF is on, we still want it to count as a NoMod replay
    for mod, is_turned_on in mods_used.items():
        
        # Ignore NM since we set it to True by default
        if mod == 'NM': continue
        
        # If it's not one of those mods but it's turned on, then the replay doesn't count as NoMod
        if mod not in ['ScoreV2', 'NF', 'SD', 'PF'] and is_turned_on:
            mods_used['NM'] = False
            break
    
    return mods_used

async def replay_has_illegal_mods(channel: discord.abc.Messageable, mods_used: dict[str, bool]) -> bool:
    """Check if replay uses a mod that is unsupported. Return True if yes, False otherwise."""
    
    # Cycle through all entries in the mods_used dict
    for mod, is_active in mods_used.items():
        
        # No need to do anything if the replay uses a mod that's accepted
        if mod in ALLOWED_REPLAY_MODS or mod == 'NM': continue
        
        # If it's not an accepted mod, we'll check whether it's turned on
        if is_active == True:
            
            # If it's turned on, we'll send a message
            new_message = "Only the following mods are supported: "
            new_message += create_str_of_allowed_replay_mods()
                
            await channel.send(new_message)
            return True
    
    return False

async def replay_is_taiko(channel: discord.abc.Messageable, replay: osrparse.Replay) -> bool:
    """Check if replay is a taiko replay. Return True if yes, False otherwise."""
    
    if replay.mode != osrparse.GameMode.TAIKO:
        await channel.send("This isn't a taiko replay!")
        return False
    return True

async def replay_is_a_convert(channel: discord.abc.Messageable, beatmap: ossapi.Beatmap) -> bool:
    """Check if replay is a convert. Return True if yes, False otherwise."""
    
    if beatmap.mode != ossapi.GameMode.TAIKO:
        await channel.send("This is a convert replay!")
        return True
    return False

async def replay_is_outdated(channel: discord.abc.Messageable, replay: osrparse.Replay) -> bool:
    """Check if replay was made in the last 24 hours. Return True if yes, False otherwise."""
    
    replay_age = datetime.datetime.now(datetime.timezone.utc) - replay.timestamp  # now() doesn't have timezone info, so we need to add it
    twenty_four_hours = datetime.timedelta(hours=24)
    
    if replay_age >= twenty_four_hours:
        await channel.send("Replay must be made within the last 24 hours!")
        return True
    return False

async def replay_is_made_by_user(conn: aiosqlite.Connection, channel: discord.abc.Messageable, osu_id_in_replay: int, discord_id: int) -> bool:
    """Check if replay was made by the user. Return True if yes, False otherwise."""
 
    cursor = await conn.cursor()
 
    # Retrieve the user's osu id using their discord id
    await cursor.execute("SELECT osu_id FROM exp_table WHERE discord_id=?", (discord_id,))
    data = await cursor.fetchone()
    
    assert data is not None
    osu_id_in_database = data[0]

    # If user's osu id in the database is different than that in the replay, that means it's not made by the user
    if osu_id_in_database != osu_id_in_replay:
        await channel.send("This replay is not made by you!")
        return False
    return True

async def replay_is_already_submitted(conn: aiosqlite.Connection, channel: discord.abc.Messageable, osu_id: int, 
                                    beatmap: ossapi.Beatmap, beatmapset: ossapi.Beatmapset, replay: osrparse.Replay) -> bool:
    """Check if replay has already been submitted by the user (ie in the replay database). Return True if yes, False otherwise."""
    
    cursor = await conn.cursor()
    
    # See if the replay database contains a row with the exact same information as the submitted replay
    query = "SELECT * FROM submitted_replays WHERE osu_id=? AND beatmap_id=? AND beatmapset_id=? AND timestamp=?"
    await cursor.execute(query, (osu_id, beatmap.id, beatmapset.id, replay.timestamp))
    replay_in_database = await cursor.fetchone()
    
    # If there is, that means the replay has already been submitted
    if replay_in_database:
        await channel.send("You already submitted this replay!")
        return True
    return False

def calculate_total_exp_gained(replay: osrparse.Replay, beatmap: ossapi.Beatmap) -> int:
    """Calculate the TOTAL exp gained from submitting a replay based on a formula."""
    
    total_exp_gained = math.pow(max(3*replay.count_300 + 0.75*replay.count_100 - 3*replay.count_miss, 0), 0.6) * math.pow(min(beatmap.difficulty_rating+1, 11), 1.2) * 0.05
    total_exp_gained = int(total_exp_gained)
    return total_exp_gained

def create_exp_bars_dict() -> dict[str, int]:
    """Returns a dict with all exp bars as keys, with their values set to 0."""
    
    # Initialize the dict
    exp_bars_dict: dict[str, int] = {} 
    
    # Add all exp bars
    for exp_bar_name in EXP_BAR_NAMES:
        exp_bars_dict[exp_bar_name] = 0
    
    return exp_bars_dict
    
def calculate_mod_exp_gained(total_exp_gained: int, exp_gained: dict[str, int], mods_used: dict[str, bool]):
    """
    Calculate the exp gained for each mod. If there are no mods, only NoMod exp will be given.
    Otherwise, split exp amongst activated relevant mods (mods with their own exp bars).
    exp_gained contains the amount of exp gained for each mod.
    """
    
    # Update the overall exp gained in the exp_gained dict
    exp_gained['Overall'] = total_exp_gained
    
    # If the replay is NoMod, allocate all exp gained to NoMod
    if mods_used['NM'] == True:
        exp_gained['NM'] = total_exp_gained
        return
    
    # Otherwise, count the number of relevant mods activated
    num_exp_bar_mods_activated: int = 0
    
    for exp_bar_name in EXP_BAR_NAMES:
        
        if exp_bar_name == 'Overall': continue
        
        # If a relevant mod is activated, increment the count
        if mods_used[exp_bar_name] == True:
            num_exp_bar_mods_activated += 1
    
    # Then evenly allocate the exp to the exp bars with their respective mods activated
    for exp_bar_name in EXP_BAR_NAMES:
        
        if exp_bar_name == 'Overall': continue

        if mods_used[exp_bar_name] == True:
            exp_gained[exp_bar_name] = total_exp_gained // num_exp_bar_mods_activated
            
def calculate_level_information(total_exp: int, return_level_only: bool = False) -> int | tuple[int, int, int]:
    """
    Given the total exp for a particular mod, calculate and return the current level, progress towards the next level, and the exp required for the next level.
    If <return_level_only> is True, only return the level.
    
    Current formula:
    You start at level 1 with 0 xp. Level 2 requires 50 exp. Level 3 requires 100 MORE exp. And so on.
    """

    current_level = 1
    exp_required_for_next_level = 50
    
    # From the total exp, deduct the exp required for each subsequent level
    while total_exp >= exp_required_for_next_level:
        current_level += 1
        total_exp -= exp_required_for_next_level
        exp_required_for_next_level += 50
        
    progress_to_next_level = total_exp
    
    if return_level_only == True:
        return current_level
    return current_level, progress_to_next_level, exp_required_for_next_level            

async def update_user_exp_and_levels_in_database(conn: aiosqlite.Connection, osu_id: int, exp_gained: dict[str, int]):
    """Update user's exp and levels in the database."""
    
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
    for mod, is_active in mods_used.items():
        
        # If that mod is not active, ignore it
        if not is_active: continue
        
        # We check for NoMod later, since NoMod can be active alongside other mods like ScoreV2 and NF
        if mod == 'NM': continue
        
        # If SD is active AND PF is active, don't display SD
        if mod == 'SD' and mods_used['PF'] == True: continue
        
        # If DT is active AND NC is active, don't display DT
        if mod == 'DT' and mods_used['NC'] == True: continue
        
        # Otherwise just add the active mod to the list
        mod_list += (f"{mod} ")
    
    # If the mod list is empty, it means that the replay is NoMod
    if mod_list == "":
        mod_list = "NoMod"
    
    return mod_list.strip()  # Removes trailing space

async def add_replay_stats_to_embed(embed: discord.Embed, beatmap: ossapi.Beatmap, beatmapset: ossapi.Beatmapset, 
                           replay: osrparse.Replay, mods_used: dict[str, bool]):
    """Add different statistics about the replay to an embed.""" 
    
    mod_list = get_mod_list(mods_used)
    accuracy = calculate_accuracy(replay)
    map_link = f"https://osu.ppy.sh/beatmapsets/{beatmapset.id}#taiko/{beatmap.id}"
    
    # Add the replay stats to the embed
    embed.title = f"Your replay has been submitted!"
    metadata = f"**[{beatmapset.artist} - {beatmapset.title} [{beatmap.version}]]({map_link})**"
    stats = f"{beatmap.difficulty_rating:.2f}* ▸ {accuracy:.2f}% ▸ `[{replay.count_300} • {replay.count_100} • {replay.count_miss}]` ▸ {mod_list}"
    
    # Combine all the text into one line, since you can't do markdown formatting (embedding map link) in the name of a field
    text = metadata + '\n' + stats
    embed.add_field(name='', value=text, inline=False)

async def add_updated_user_exp_to_embed(conn: aiosqlite.Connection, embed: discord.Embed, osu_id: int, exp_gained: dict[str, int]):
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
    
    # Loop through all exp bars
    for mod in EXP_BAR_NAMES:
        
        # Only display the mod exp if you gained exp for it
        if exp_gained[mod] != 0:
            current_level, progress_to_next_level, exp_required_for_next_level = calculate_level_information(total_exp[mod])  # type: ignore
            
            # Add mod exp information to the embed
            name = f"{mod} Level {current_level}:\n"
            value = f"{progress_to_next_level} / {exp_required_for_next_level} **(+{exp_gained[mod]})**\n"  # [Progress to next level in exp / Required exp for next level]
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
        
        # Give users the ability to submit multiple replays in one message
        for attachment in message.attachments:
            
            # Record the time it takes to submit one replay
            start_time = datetime.datetime.now()
            
            # Reuse the same connection for the same replay
            async with aiosqlite.connect("./data/database.db") as conn:
            
                if not await user_is_verified(conn, channel, discord_id):
                    break
                
                # Skip attachment if it's not a replay (doesn't contain ".osr" at the end)
                # https://regex-vis.com/?r=.*%3F%5C.osr
                if re.match(r".*?\.osr", attachment.filename) is None: continue
                
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
                except Exception as error:
                    await channel.send(f"Failed to parse replay: {error}")
                    continue
                finally:
                    file.close()
                    os.remove(pathname)  # Delete the file
                
                # Retrieve beatmap information
                try:
                    beatmap = await osu_api.beatmap(checksum=replay.beatmap_hash)
                    beatmapset = await osu_api.beatmapset(beatmap_id=beatmap.id)
                except:
                    await channel.send("Map is not submitted!")
                    continue
                    
                # Retrieve user information
                try:
                    osu_user = await osu_api.user(user=replay.username)
                    osu_id = osu_user.id
                except:
                    await channel.send("Can't find user!")
                    continue
                
                # Get mods used: https://kszlim.github.io/osu-replay-parser/_modules/osrparse/utils.html#Mod
                # Mods are stored as a bit string
                mods_used = determine_mods_used(replay)
                
                # A series of checks to determine the validity of the replay
                if (await replay_has_illegal_mods(channel, mods_used)
                or await replay_is_a_convert(channel, beatmap)
                or await replay_is_outdated(channel, replay)
                or await replay_is_already_submitted(conn, channel, osu_id, beatmap, beatmapset, replay)
                or not await replay_is_taiko(channel, replay)
                or not await replay_is_made_by_user(conn, channel, osu_id, discord_id)):
                    continue

                # Calculate exp gained for each mod
                # If there is more than one mod active, exp is evenly split between them
                total_exp_gained = calculate_total_exp_gained(replay, beatmap)
                exp_gained = create_exp_bars_dict()
                calculate_mod_exp_gained(total_exp_gained, exp_gained, mods_used)
                
                # Edit the database
                await update_user_exp_and_levels_in_database(conn, osu_id, exp_gained)
                await add_replay_to_database(conn, osu_id, beatmap, beatmapset, replay)
                
                # Commit all database changes
                await conn.commit()
                
                # Initialize the embed to be sent
                embed = discord.Embed()
                
                # Add information to the embed
                await add_replay_stats_to_embed(embed, beatmap, beatmapset, replay, mods_used)
                await add_updated_user_exp_to_embed(conn, embed, osu_id, exp_gained)
                
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
            
            # Otherwise, check if the username exists in the database
            else:
                await cursor.execute("SELECT 1 FROM exp_table WHERE osu_username=?", (username,))
                data = await cursor.fetchone()
                if data is None:
                    await interaction.response.send_message("User not found!")
                    return
                
            # Fetch user's exp in each mod
            await cursor.execute("SELECT overall_exp, nm_exp, hd_exp, hr_exp FROM exp_table WHERE osu_username=?", (username,))
            data = await cursor.fetchone()
            
            total_exp = create_exp_bars_dict()
        
            assert data is not None
            total_exp['Overall'] = data[0]
            total_exp['NM'] = data[1]
            total_exp['HD'] = data[2]
            total_exp['HR'] = data[3]
        
            # Fetch user's level in each mod
            await cursor.execute("SELECT overall_level, nm_level, hd_level, hr_level FROM exp_table WHERE osu_username=?", (username,))
            data = await cursor.fetchone()
            
            level = create_exp_bars_dict()
            
            assert data is not None
            level['Overall'] = data[0]
            level['NM'] = data[1]
            level['HD'] = data[2]
            level['HR'] = data[3]
        
        # Initialize embed
        embed = discord.Embed(title=f"{username}'s EXP Stats", colour=discord.Colour.blurple())
        
        # Display user's mod exp by looping through all mods
        for mod_name in EXP_BAR_NAMES:  # Combine the "Overall" word with the relevant mods list
            
            # Calculate relevant display information
            current_level, progress_to_next_level, exp_required_for_next_level = calculate_level_information(total_exp[mod_name])  # type: ignore
            progress_in_percentage: float = (progress_to_next_level / exp_required_for_next_level) * 100
            
            # Add exp information for that mod to the embed
            name_info = f"{mod_name} Level {current_level}:\n"
            value_info = f"{progress_to_next_level} / {exp_required_for_next_level} ({progress_in_percentage:.2f}%)\n"  # Progress to next level in exp / Required exp for next level
            
            # We want the overall exp to be in its own separate line
            if mod_name == "Overall":
                embed.add_field(name=name_info, value=value_info, inline=False)
            else:
                embed.add_field(name=name_info, value=value_info)
                                
        # Display exp
        await interaction.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(GameCog(bot))