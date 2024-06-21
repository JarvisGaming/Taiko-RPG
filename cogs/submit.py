import datetime
import os
import typing

import aiohttp
import aiosqlite
import discord
import dotenv
from classes.score import Score
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from other.global_constants import *
from other.utility import *


async def refresh_access_token(session: aiohttp.ClientSession):
    """
    should be turned into a looping task on startup
    https://osu.ppy.sh/docs/index.html#using-the-access-token-to-access-the-api
    """

    headers = {
        'Accept': "application/json",
        'Content-Type': "application/x-www-form-urlencoded",
    }
    data = {
        'client_id': OSU_CLIENT_ID,
        'client_secret': OSU_CLIENT_SECRET,
        'grant_type': "client_credentials",
        'scope': "public",
    }
    
    async with session.post("https://osu.ppy.sh/oauth/token", headers=headers, data=data) as resp:
        json_file = await resp.json()
        dotenv.set_key(dotenv_path="./data/sensitive.env", key_to_set="OSU_API_ACCESS_TOKEN", value_to_set=json_file['access_token'])

class SubmitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="submit", description="Submit recent scores that you've made, including failed scores.")
    @app_commands.describe(number_of_scores_to_submit="How many recent scores you want to submit. Leave blank to submit all.")
    @is_verified()
    async def submit(self, interaction: discord.Interaction, number_of_scores_to_submit: int = 10000):
        
        session = aiohttp.ClientSession()
        await refresh_access_token(session)
        
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'x-api-version': "20220705",  # get modern score return info
            'Authorization': f"Bearer {os.getenv('OSU_API_ACCESS_TOKEN')}",
        }
        
        user_osu_id = await get_osu_id_from_discord_id(interaction.user.id)
        url = f"https://osu.ppy.sh/api/v2/users/{user_osu_id}/scores/recent?include_fails=1&mode=taiko&limit={number_of_scores_to_submit}"
        
        async with session.get(url, headers=headers) as resp:
            parsed_response = await resp.json()
            webhook = interaction.followup  # We can use webhook.send to send followup messages
            file = open("./data/scores.txt", "w")

            message_content = f"Processing {len(parsed_response)} scores...\n"
            if len(parsed_response) >= 20:
                message_content += "The bot will get rate limited on large submissions. Please be patient!"
            await interaction.response.send_message(content=message_content)
            
            for score_info in parsed_response:
                score = Score(score_info, interaction.user.id)
                
                if not await self.score_is_valid(webhook, score):
                    return
        
                self.write_one_score_to_debug_file(file, score)
                await self.process_one_score(webhook, score)
                await self.display_one_score(webhook, score)
            file.close()
            
            # Add total exp gained after all submissions
            await webhook.send("All done!")
            
        await session.close()

    def write_one_score_to_debug_file(self, file: typing.TextIO, score: Score):
        file.write(f"OVERALL:\n")
        attributes = vars(score)
        for key, value in attributes.items():
            file.write(f"{key}: {value}\n")

        file.write("\nMODS:\n")
        for mod in score.mods:
            file.write(f"{mod.acronym}: {mod.settings}\n")
                    
        file.write("\nBEATMAP\n")
        attributes = vars(score.beatmap)
        for key, value in attributes.items():
            file.write(f"{key}: {value}\n")
                    
        file.write("\nBEATMAPSET\n")
        attributes = vars(score.beatmapset)
        for key, value in attributes.items():
            file.write(f"{key}: {value}\n")
        
        file.write("\nEXP\n")
        for key, value in score.exp_gained.items():
            file.write(f"{key}: {value}\n")
                    
        file.write("\n\n\n\n\n")

    async def process_one_score(self, webhook: discord.Webhook, score: Score):
        
        async with aiosqlite.connect("./data/database.db") as conn:
            # Edit the database
            await self.add_replay_to_database(conn, score)
            await self.update_user_exp_bars_in_database(conn, score)
            
            # Commit all database changes
            await conn.commit()

    async def score_is_valid(self, webhook: discord.Webhook, score: Score) -> bool:
        validation_failed_message = f"Ignoring **{score.beatmapset.artist} - {score.beatmapset.title} [{score.beatmap.difficulty_name}]**\n"
        validation_failed_message += "Reason: "
        
        if await score.is_already_submitted():
            validation_failed_message += "Score is already submitted"
            await webhook.send(validation_failed_message)
            return False

        elif score.is_convert:
            validation_failed_message += "Score is a convert"
            await webhook.send(validation_failed_message)
            return False
        
        elif score.has_illegal_mods():
            validation_failed_message += "Score contains disallowed mods. The only allowed mods are: " + create_str_of_allowed_replay_mods()
            await webhook.send(validation_failed_message)
            return False
        
        elif score.has_illegal_dt_ht_rates():
            validation_failed_message += "DT must be set to x1.5 speed, and HT must be set to x0.75 speed"
            await webhook.send(validation_failed_message)
            return False
        
        return True
    
    async def add_replay_to_database(self, conn: aiosqlite.Connection, score: Score):
        query = "INSERT INTO submitted_replays VALUES (?, ?, ?, ?)"
        await conn.execute(query, (score.user_osu_id, score.beatmap.id, score.beatmapset.id, score.timestamp))
    
    async def update_user_exp_bars_in_database(self, conn: aiosqlite.Connection, score: Score):
        user_exp_bars = await get_user_exp_bars(score.user_discord_id)
        
        # Update dict of ExpBar objects
        for exp_bar_name, amount_of_exp_gained in score.exp_gained.items():
            if amount_of_exp_gained > 0:
                user_exp_bars[exp_bar_name].add_exp_to_expbar(amount_of_exp_gained)
        
        # Write to db
        cursor = await conn.cursor()
        for exp_bar_name, exp_bar in user_exp_bars.items():
            query = f"UPDATE exp_table SET {exp_bar_name.lower()}_exp=?, {exp_bar_name.lower()}_level=? WHERE osu_id=?"
            await cursor.execute(query, (exp_bar.total_exp, exp_bar.level, score.user_osu_id))
    
    async def display_one_score(self, webhook: discord.Webhook, score: Score):
        # Initialize the embed to be sent
        embed = discord.Embed()
        
        # Add information to the embed
        embed.title = f"{score.username} submitted a new score:"
        await self.add_metadata_and_score_stats_to_embed(embed, score)
        await self.add_updated_user_exp_to_embed(embed, score)
        await webhook.send(embed=embed)
    
    async def add_metadata_and_score_stats_to_embed(self, embed: discord.Embed, score: Score):
        metadata = f"**[{score.beatmapset.artist} - {score.beatmapset.title} [{score.beatmap.difficulty_name}]]({score.beatmap.url})**"
        score_stats = f"{score.beatmap.sr:.2f}* ▸ "
        score_stats += f"{score.accuracy:.2f}% ▸ "
        score_stats += f"`[{score.num_300s} • {score.num_100s} • {score.num_misses}]` ▸ "
        score_stats += f"{score.mods_human_readable}"
        
        # Put the metadata in "value", since you can't use markdown syntax to link url in "name"
        text = metadata + '\n' + score_stats
        embed.add_field(name='', value=text, inline=False)  
    
    async def add_updated_user_exp_to_embed(self, embed: discord.Embed, score: Score):
        user_exp_bars = await get_user_exp_bars(score.user_discord_id)
        
        for exp_bar_name, amount_of_exp_gained in score.exp_gained.items():
            if amount_of_exp_gained > 0:
                level = user_exp_bars[exp_bar_name].level
                exp_progress_to_next_level = user_exp_bars[exp_bar_name].exp_progress_to_next_level
                exp_required_for_next_level = user_exp_bars[exp_bar_name].exp_required_for_next_level
                
                embed_name = f"{exp_bar_name} Level {level}"
                embed_value = f"{exp_progress_to_next_level}/{exp_required_for_next_level} **(+{score.exp_gained[exp_bar_name]})**"
                
                embed.add_field(name=embed_name, value=embed_value)
        
    
async def setup(bot: commands.Bot):
    await bot.add_cog(SubmitCog(bot))