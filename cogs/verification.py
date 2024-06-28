import inspect
import re

import ossapi
from discord import app_commands
from discord.ext import commands
from ossapi import UserLookupKey
from other.global_constants import *
from other.utility import *


class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Sign up using this command!")
    @app_commands.describe(profile_link="Your osu profile link")
    async def verify(self, interaction: discord.Interaction, profile_link: str):
        """Verifies user and adds them to the database."""

        osu_id = self.get_osu_id_from_profile_link(profile_link)
        if osu_id is None:
            await interaction.response.send_message("Profile link should be in the format of `https://osu.ppy.sh/users/<user id>`")
            return
        
        try:
            osu_user = await osu_api.user(osu_id, key=UserLookupKey.ID)
        except ValueError:
            await interaction.response.send_message("User does not exist!")
            return
        except Exception as error:
            await interaction.response.send_message(f"An exception occured: {error}")
            return
        
        if not await self.osu_profile_discord_field_is_correct(interaction, osu_user):
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
            
            if await self.user_is_already_verified(osu_user, cursor):
                await interaction.response.send_message("You are already verified!")
                return
        
            await self.add_user_to_database(interaction, osu_user, cursor)
            await conn.commit()
        
        await interaction.response.send_message("Verification successful! Use the `/help` command to see where to start!")

    def get_osu_id_from_profile_link(self, profile_link: str) -> str | None:
        """
        Returns the user id part of "https://osu.ppy.sh/users/<user id>". Returns None if there is no match.
        https://regex-vis.com/?r=https%3A%2F%2Fosu%5C.ppy%5C.sh%2Fusers%2F%28%5B0-9%5D%2B%29
        """
        regex_check = r"https://osu\.ppy\.sh/users/([0-9]+)"  
        match = re.match(regex_check, profile_link)

        if match is None:
            return None
        return match.group(1)  # Gets the ID part from the link

    async def osu_profile_discord_field_is_correct(self, interaction: discord.Interaction, osu_user: ossapi.User) -> bool:
        if interaction.user.name != osu_user.discord:
            return False
        return True

    async def user_is_already_verified(self, osu_user: ossapi.User, cursor: aiosqlite.Cursor):
        await cursor.execute("SELECT osu_id FROM exp_table WHERE osu_id=?", (osu_user.id,))
        if await cursor.fetchone() is not None:
            return True
        return False
    
    async def add_user_to_database(self, interaction: discord.Interaction, osu_user: ossapi.User, cursor: aiosqlite.Cursor):
        query = "INSERT INTO exp_table(osu_username, osu_id, discord_id) VALUES (?, ?, ?)"
        await cursor.execute(query, (osu_user.username, osu_user.id, interaction.user.id))

    @app_commands.command(name="update_osu_username", description="If you got a username change on osu, use this to update your name in the bot.")
    @is_verified()  # is_verified checks using discord_id, so we can use it here
    async def update_osu_username(self, interaction: discord.Interaction):
        osu_id = await get_osu_id(discord_id=interaction.user.id)
        assert osu_id is not None
        
        try:
            osu_user = await osu_api.user(osu_id, key=UserLookupKey.ID)
        except ValueError:
            await interaction.response.send_message("User does not exist!")
            return
        except Exception as error:
            await interaction.response.send_message(f"An exception occured: {error}")
            return
        
        async with aiosqlite.connect("./data/database.db") as conn:
            await conn.execute("UPDATE exp_table SET osu_username=? WHERE discord_id=?", (osu_user.username, interaction.user.id))
            await conn.commit()
        
        await interaction.response.send_message("Username updated successfully!")

    @app_commands.command(name="update_discord_account", description="If you're using a new discord account, use this to update your discord id in the bot.")
    async def update_discord_account(self, interaction: discord.Interaction, profile_link: str):
        osu_id = self.get_osu_id_from_profile_link(profile_link)
        if osu_id is None:
            await interaction.response.send_message("Profile link should be in the format of `https://osu.ppy.sh/users/<user id>`")
            return
        
        try:
            osu_user = await osu_api.user(osu_id, key=UserLookupKey.ID)
        except ValueError:
            await interaction.response.send_message("User does not exist!")
            return
        except Exception as error:
            await interaction.response.send_message(f"An exception occured: {error}")
            return
        
        if not await self.osu_profile_discord_field_is_correct(interaction, osu_user):
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
            await cursor.execute("SELECT 1 FROM exp_table WHERE osu_id=?", (osu_id,))
            if await cursor.fetchone() is None:
                await interaction.response.send_message("You are not verified!")
                return

            await cursor.execute("UPDATE exp_table SET discord_id=? WHERE osu_id=?", (interaction.user.id, osu_id))
            await conn.commit()
        
        await interaction.response.send_message("Discord account updated successfully!")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))