import discord
from discord import app_commands

from ossapi import UserLookupKey
from discord.ext import commands

import re

from other.global_constants import *

class SecretsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Emoji, user: discord.User):
        """Sends a message when someone reacts with the middle finger emoji to a bot message."""
        
        if reaction.message.author.id != BOT_ID:  # type: ignore
            return
            
        if str(reaction) == "🖕":
            channel = reaction.message.channel  # type: ignore
            await channel.send(f"{user.mention} 🖕🖕🖕")
    
    @commands.Cog.listener(name="on_message")
    async def wysi(self, message: discord.Message):
        """Sends a message when a new message contains the number 727: https://knowyourmeme.com/memes/727-wysi"""
        
        # Bot may send messages with 727 in them (eg score)
        if message.author.id == BOT_ID:
            return
        
        # Removes the <@xxx> part(s) in the message, which are pings
        # https://regex-vis.com/?r=%3C%40%5B0-9%5D%2B%3F%3E
        message_without_pings = re.sub("<@[0-9]+?>", "", message.content)
        
        if "727" in message_without_pings:
            channel = message.channel
            await channel.send("WHEN YOU SEE IT")
        

async def setup(bot):
    await bot.add_cog(SecretsCog(bot))