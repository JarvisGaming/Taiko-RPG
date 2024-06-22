import re

import discord
from discord import app_commands
from discord.ext import commands
from ossapi import UserLookupKey
from other.global_constants import *


class SecretsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener(name="on_message")
    async def wysi(self, message: discord.Message):
        """Sends a message when a new message contains the number 727: https://knowyourmeme.com/memes/727-wysi"""
        
        message_without_pings = message.content
        
        # Removes the <@xxx> part(s) in the message, which are pings
        # https://regex-vis.com/?r=%3C%40%5B0-9%5D%2B%3F%3E
        message_without_pings = re.sub("<@[0-9]+?>", "", message_without_pings)
        
        # Removes the :xxx: part(s) in the message, which are emojis
        # https://regex-vis.com/?r=%3A%5Cw%2B%3F%3A
        message_without_pings = re.sub(r":\w+?:", "", message_without_pings)
        
        if any(word in message_without_pings for word in ["727", "7.27", "72.7"]):
            channel = message.channel
            await channel.send("WHEN YOU SEE IT")
            return
        

async def setup(bot: commands.Bot):
    await bot.add_cog(SecretsCog(bot))