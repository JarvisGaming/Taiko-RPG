import datetime
import math
import re
import uuid  # Generate random file names

import discord
import osrparse
import ossapi
from discord import app_commands
from discord.ext import commands
from other.global_constants import *
from other.utility import *


def create_exp_bars_dict() -> dict[str, int]:
    """Returns a dict with all exp bars as keys, with their values set to 0."""
    
    # Initialize the dict
    exp_bars_dict: dict[str, int] = {} 
    
    # Add all exp bars
    for exp_bar_name in EXP_BAR_NAMES:
        exp_bars_dict[exp_bar_name] = 0
    
    return exp_bars_dict
            
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

class GameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener(name="on_message")
    async def old_submit(self, message: discord.Message):
        """When replay file is posted, redirect user to use /submit."""
        
        # Skip attachment if it's not a replay (doesn't contain ".osr" at the end)
        # https://regex-vis.com/?r=.*%3F%5C.osr
        for attachment in message.attachments:
            if re.match(r".*?\.osr", attachment.filename) is not None:
                await message.channel.send("We've switched to using `/submit`!")
                return

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
        
async def setup(bot: commands.Bot):
    await bot.add_cog(GameCog(bot))