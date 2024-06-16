import discord
import inspect
from discord import app_commands
from discord.ext import commands

from other.global_constants import *
from other.utility import create_str_of_allowed_replay_mods

class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Don't know where to start?")
    async def help(self, interaction: discord.Interaction):
        """Responds with a message explaning how to use the bot."""
        
        embed = discord.Embed(title="How to play")
        embed.add_field(name="1. Verify yourself", value="Use `/verify <profile link>` to get started!", inline=False)
           
        # Adds all currently accepted mods to the text
        mod_list = create_str_of_allowed_replay_mods()
        text =  f"""
                Drag your replays into this channel to submit them!
                (You can submit multiple at a time!)
                
                You get EXP for each replay you submit.
                The only restrictions for replays are:
                - Replays have to be made in the last 24 hours
                - Replays have to be made on submitted maps
                - Your replay doesn't have to be a pass
                - Mods that are currently allowed: {mod_list}
                """ 
        text = inspect.cleandoc(text)  # Removes weird indentation of doc strings
        embed.add_field(name="2. Submit replays", value=text, inline=False)
        
        embed.add_field(name="3. See your stats", value="Use the `/profile` command to see how much EXP you have!", inline=False)
        embed.add_field(name="4. Check the leaderboards", value="Use the `/leaderboard` command to see where you place on the leaderboard!", inline=False)
        embed.add_field(name="5. Found a bug? Have any suggestions?", value="Talk about it in the #suggest-and-complain channel!", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(MiscCog(bot))