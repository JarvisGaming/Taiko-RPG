from typing import Optional

import discord
import other.utility
from classes.exp import ExpBar
from discord import app_commands
from discord.ext import commands
from init.currency_init import init_currency
from other.global_constants import *


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="profile", description="Display all of a user's exp information")
    @app_commands.describe(osu_username="The player that you want to see the profile of (case sensitive). Leave blank to see your own.")
    @other.utility.is_verified()
    async def profile(self, interaction: discord.Interaction, osu_username: Optional[str] = None):
        
        # osu_username is an optional field
        if osu_username is None:
            osu_username = await other.utility.get_osu_username(discord_id=interaction.user.id)
        
        # Check if the user is in the database
        if not await other.utility.user_is_in_database(osu_username=osu_username):
            await interaction.response.send_message("Player not found!")
            return
        
        # osu_id is needed to search data in the currency table
        osu_id = await other.utility.get_osu_id(osu_username=osu_username)
        assert osu_id is not None
        
        user_currency = await other.utility.get_user_currency(osu_id=osu_id)
        user_exp_bars = await other.utility.get_user_exp_bars(osu_username=osu_username)
        embed = discord.Embed(title=f"{osu_username}'s Profile", colour=discord.Colour.blurple())
        
        self.populate_profile_embed(user_currency, user_exp_bars, embed)
        
        await interaction.response.send_message(embed=embed)

    def populate_profile_embed(self, user_currency: dict[str, int], user_exp_bars: dict[str, ExpBar], embed: discord.Embed):
        for currency_id, currency_amount in user_currency.items():
            all_currencies = init_currency()
            embed.add_field(name='', value=f"{currency_amount} {all_currencies[currency_id].animated_discord_emoji}", inline=False)
        
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

async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))