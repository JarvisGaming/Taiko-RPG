import inspect

import discord
from discord import app_commands
from discord.ext import commands
from other.global_constants import *


class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="help", description="Don't know where to start?")
    async def help(self, interaction: discord.Interaction):
        """Responds with a message explaning how to use the bot."""
        
        embed = discord.Embed(title="How to play")
        embed.add_field(name="1. Verify yourself", value="Use `/verify <profile link>` to get started!", inline=False)
           
        # Adds all currently accepted mods to the text
        text =  f"""
                Use the `/submit` command to submit scores made in the past 24 hours!
                **Warning: You can only submit your most recent 100 scores. This is an osu API limitation. Please submit regularly.**
                
                Note that only the following mods are allowed:
                **Difficulty Reducing Mods:**
                NF EZ HT
                **Difficulty Increasing Mods:**
                HR SD PF DT NC HD FL
                **Other Mods:**
                CL AC SG MU
                """
        text = inspect.cleandoc(text)  # Removes weird indentation of doc strings
        embed.add_field(name="2. Submit scores", value=text, inline=False)
        
        embed.add_field(name="3. See your stats", value="Use the `/profile` command to see how much EXP you have!", inline=False)
        embed.add_field(name="4. Check the leaderboards", value="Use the `/leaderboard` command to see where you place on the leaderboard!", inline=False)
        embed.add_field(name="5. Found a bug? Have any suggestions?", value="Talk about it in the #suggest-and-complain channel!", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCog(bot))