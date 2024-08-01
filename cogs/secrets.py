import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands
from other.global_constants import *


class SecretsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener(name="on_message")
    async def wysi(self, message: discord.Message):
        """Sends a message when a new message contains the number 727: https://knowyourmeme.com/memes/727-wysi"""
        
        message_after_cleaning = message.content
        
        # Removes the <@xxx> part(s) in the message, which are pings and emotes
        # https://regex-vis.com/?r=%3C.%2B%3F%3E
        message_after_cleaning = re.sub(r"<.+?>", "", message_after_cleaning)
        
        # Removes the [...](...) part(s) in the message, which are animated emotes / markdown for images and gifs
        # https://regex-vis.com/?r=%5C%5B.%2B%3F%5C%5D%5C%28.%2B%3F%5C%29
        message_after_cleaning = re.sub(r"\[.+?\]\(.+?\)", "", message_after_cleaning)
        
        if any(word in message_after_cleaning for word in ["727", "7.27", "72.7", "7/27"]):
            channel = message.channel
            await channel.send("WHEN YOU SEE IT")
            return
        
    @app_commands.command(name="secret", description="what's it gonna be?")
    async def random(self, interaction: discord.Interaction):
        """Displays a random piece of media."""
        
        num_images = len(os.listdir("../RPG common data/secrets_data/images"))
        num_texts = len(os.listdir("../RPG common data/secrets_data/songs"))
        num_videos = len(os.listdir("../RPG common data/secrets_data/texts"))
        num_songs = len(os.listdir("../RPG common data/secrets_data/videos"))
        
        # This is a weighted choice, so if there are more texts, then texts are more likely to be chosen and vice versa
        type_to_display = random.choices(["image", "text", "video", "song"], weights=[num_images, num_texts, num_videos, num_songs])[0]
        
        if type_to_display == "image":
            filename = random.choices(os.listdir("../RPG common data/secrets_data/images"))[0]
            with open(f"../RPG common data/secrets_data/images/{filename}", "rb") as file:
                file = discord.File(file)
                await interaction.response.send_message(file=file, ephemeral=True)
                
        elif type_to_display == "text":
            filename = random.choices(os.listdir("../RPG common data/secrets_data/texts"))[0]
            with open(f"../RPG common data/secrets_data/texts/{filename}", "r") as file:
                text_selected = file.read()
                await interaction.response.send_message(text_selected, ephemeral=True)
        
        elif type_to_display == "video":
            filename = random.choices(os.listdir("../RPG common data/secrets_data/videos"))[0]
            with open(f"../RPG common data/secrets_data/videos/{filename}", "rb") as file:
                file = discord.File(file)
                await interaction.response.send_message(file=file, ephemeral=True)
        
        elif type_to_display == "song":
            filename = random.choices(os.listdir("../RPG common data/secrets_data/songs"))[0]
            with open(f"../RPG common data/secrets_data/songs/{filename}", "r") as file:
                text_selected = file.read()
                await interaction.response.send_message(text_selected, ephemeral=True)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(SecretsCog(bot))