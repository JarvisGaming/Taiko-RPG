import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from other.global_constants import *
from other.utility import *


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="profile", description="Display all of a user's exp information")
    @app_commands.describe(osu_username="The player that you want to see the profile of (case sensitive). Leave blank to see your own.")
    @is_verified()
    async def profile(self, interaction: discord.Interaction, osu_username: str | None = None):
        
        # osu_username is an optional field
        if osu_username is None:
            osu_username = await get_osu_username(discord_id=interaction.user.id)
            
        user_exp_bars = await get_user_exp_bars(osu_username=osu_username)
        embed = discord.Embed(title=f"{osu_username}'s EXP Stats", colour=discord.Colour.blurple())
        
        for exp_bar_name, exp_bar in user_exp_bars.items():
            # Add exp information for that mod to the embed
            progress_in_percentage = exp_bar.exp_progress_to_next_level / exp_bar.exp_required_for_next_level * 100
            name_info = f"{exp_bar_name} Level {exp_bar.level}:\n"
            value_info = f"{exp_bar.exp_progress_to_next_level} / {exp_bar.exp_required_for_next_level} ({progress_in_percentage:.2f}%)\n"
            
            # We want the overall exp to be in its own separate line
            if exp_bar_name == "Overall":
                embed.add_field(name=name_info, value=value_info, inline=False)
            else:
                embed.add_field(name=name_info, value=value_info)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))