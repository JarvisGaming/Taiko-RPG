from ossapi import UserLookupKey
from discord.ext import commands
from discord import app_commands

import re
import inspect

from other.global_constants import *
from other.utility import *

class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Sign up using this command!")
    @app_commands.describe(profile_link="Your osu profile link")
    async def verify(self, interaction: discord.Interaction, profile_link: str):
        """Verifies user and adds them to the database."""
        
        # Checks if link matches the format "https://osu.ppy.sh/users/<user id>"
        # https://regex-vis.com/?r=https%3A%2F%2Fosu%5C.ppy%5C.sh%2Fusers%2F%28%5B0-9%5D%2B%29
        regex_check = r"https://osu\.ppy\.sh/users/([0-9]+)"  
        match = re.match(regex_check, profile_link)

        # Check if format of link is incorrect
        if match is None:
            await interaction.response.send_message("Profile link should be in the format of `https://osu.ppy.sh/users/<user id>`")
            return
        
        id = match.group(1)  # Gets the ID part of the link
        
        # Get osu user using id
        try:
            osu_user = await osu_api.user(id, key=UserLookupKey.ID)
        except ValueError:
            await interaction.response.send_message("User does not exist!")
            return
        except Exception as error:
            await interaction.response.send_message(f"An exception occured: {error}")
            return
        
        # Check if discord name in osu profile is incorrect
        if interaction.user.name != osu_user.discord:
            message =   f"""
                        Your discord username is: {interaction.user.name}
                        Your osu profile's discord field is: {osu_user.discord}
                        Please fill in the correct discord name in your osu profile!
                        (You can unset it after you verify yourself.)
                        """
            message = inspect.cleandoc(message)  # Removes weird identation of triple quote strings
            await interaction.response.send_message(message) 
            return
        
        async with aiosqlite.connect("./data/database.db") as conn:
            cursor = await conn.cursor()
            
            # Check if user is already verified
            await cursor.execute("SELECT osu_id FROM exp_table WHERE osu_id=?", (osu_user.id,))
            if await cursor.fetchone() is not None:
                await interaction.response.send_message("You are already verified!")
                return
        
            # Add user to database
            query = "INSERT INTO exp_table(osu_username, osu_id, discord_id) VALUES (?, ?, ?)"
            await cursor.execute(query, (osu_user.username, osu_user.id, interaction.user.id))
            
            await conn.commit()
        
        await interaction.response.send_message("Verification successful! Use the `/help` command to see where to start!")

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))