import os
import re
import typing
from typing import Any

import aiosqlite
import discord
from classes.score import Score
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from other.global_constants import *
from other.utility import *


class SubmitCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener(name="on_message")
    async def old_submit(self, message: discord.Message):
        """When replay file is posted, redirect user to use /submit."""
        
        # Skip attachment if it's not a replay (doesn't contain ".osr" at the end)
        # https://regex-vis.com/?r=.*%3F%5C.osr
        for attachment in message.attachments:
            if re.match(r".*?\.osr", attachment.filename) is not None:
                await message.channel.send("We've switched to using `/submit`!")
                return
    
    @app_commands.command(name="submit", description="Submit recent scores that you've made, including failed scores.")
    @app_commands.describe(display_each_score="Whether you want to display the details of each score.")
    @app_commands.choices(display_each_score=[
        Choice(name="Yes", value=1),  # Choices can't be bool
        Choice(name="No", value=0)
    ])
    @app_commands.describe(number_of_scores_to_submit="How many recent scores you want to submit (capped at 100). Leave blank to submit up to 100.")
    @app_commands.checks.cooldown(rate=1, per=300.0)
    @is_verified()
    async def submit(self, interaction: discord.Interaction, display_each_score: Choice[int], number_of_scores_to_submit: int = 100):
        
        user_exp_bars_before_submission = await get_user_exp_bars(discord_id=interaction.user.id)
        webhook = interaction.followup
        
        # Slash commands time out after 3 seconds, so we send a response first in case the API requests take too long
        await interaction.response.send_message("Finding scores...")
        all_scores = await self.fetch_user_scores(interaction, number_of_scores_to_submit)
        await self.display_num_scores_fetched(interaction, display_each_score, all_scores)
        await self.process_and_display_score_impl(webhook, display_each_score, all_scores)
        await self.display_total_exp_change(interaction, user_exp_bars_before_submission, webhook)

    async def fetch_user_scores(self, interaction: discord.Interaction, number_of_scores_to_submit: int):
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'x-api-version': "20220705",  # get modern score return info
            'Authorization': f"Bearer {os.getenv('OSU_API_ACCESS_TOKEN')}",
        }
        
        user_osu_id = await get_osu_id(discord_id=interaction.user.id)
        url = f"https://osu.ppy.sh/api/v2/users/{user_osu_id}/scores/recent?include_fails=1&mode=taiko&limit={number_of_scores_to_submit}"
        
        async with http_session.conn.get(url, headers=headers) as resp:
            parsed_response = await resp.json()
            return parsed_response

    async def display_num_scores_fetched(self, interaction: discord.Interaction, display_each_score: Choice[int], all_scores: list[dict[str, Any]]):
        message_content = f"{len(all_scores)} score(s) found!\n"
        if len(all_scores) >= 30 and display_each_score.value:
            message_content += "This might take a while. You can speed it up by setting `display_each_score` to No."
            
        # You have to fetch the original response to edit it (for some reason)
        original_response = await interaction.original_response()
        await original_response.edit(content=message_content)

    async def process_and_display_score_impl(self, webhook: discord.Webhook, display_each_score: Choice[int], all_scores: list[dict[str, Any]]):
        file = open("./data/scores.txt", "w")
        
        for score_info in all_scores:
            score = await Score.create_score_object(score_info)
            self.write_one_score_to_debug_file(file, score)

            if not await self.score_is_valid(webhook, score, display_each_score):
                continue
            
            if display_each_score.value:
                await self.display_one_score(webhook, score)
            
            await self.process_one_score_in_database(score)
            
        file.close()
        await webhook.send("All done!")

    async def display_total_exp_change(self, interaction: discord.Interaction, user_exp_bars_before_submission: dict[str, ExpBar], webhook: discord.Webhook):
        user_exp_bars_after_submission = await get_user_exp_bars(discord_id=interaction.user.id)
        osu_username = await get_osu_username(discord_id=interaction.user.id)
        embed = discord.Embed(title=f"{osu_username}'s EXP changes:")
        embed.colour = discord.Color.from_rgb(255,255,255)  # white
        
        self.add_relevant_exp_bars_to_exp_change_embed(user_exp_bars_before_submission, user_exp_bars_after_submission, embed)
        
        if len(embed.fields) == 0:
            embed.add_field(name="No changes!", value='')
        await webhook.send(embed=embed)

    def add_relevant_exp_bars_to_exp_change_embed(self, user_exp_bars_before_submission: dict[str, ExpBar], 
                                                  user_exp_bars_after_submission: dict[str, ExpBar], embed: discord.Embed):
        for (exp_bar_name, exp_bar_before), exp_bar_after in zip(user_exp_bars_before_submission.items(), user_exp_bars_after_submission.values()):
            if exp_bar_after.total_exp > exp_bar_before.total_exp:
                name_info = f"{exp_bar_name} Level {exp_bar_before.level} "
                if exp_bar_after.level > exp_bar_before.level:
                    name_info += f"→ {exp_bar_after.level} (+{exp_bar_after.level - exp_bar_before.level})"
                
                value_info = f"EXP: {exp_bar_before.total_exp} → {exp_bar_after.total_exp} (+{exp_bar_after.total_exp - exp_bar_before.total_exp})"
                
                embed.add_field(name=name_info, value=value_info, inline=False)

    def write_one_score_to_debug_file(self, file: typing.TextIO, score: Score):
        """This is purely for debugging purposes."""
        
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

    async def process_one_score_in_database(self, score: Score):
        
        async with aiosqlite.connect("./data/database.db") as conn:
            await self.add_score_to_database(conn, score)
            await self.update_user_exp_bars_in_database(conn, score)
            await conn.commit()

    async def score_is_valid(self, webhook: discord.Webhook, score: Score, display_each_score: Choice[int]) -> bool:
        validation_failed_message = f"Ignoring **{score.beatmapset.artist} - {score.beatmapset.title} [{score.beatmap.difficulty_name}]**\n"
        validation_failed_message += "Reason: "
        
        if await score.is_already_submitted():
            validation_failed_message += "Score is already submitted"
            
        elif score.is_convert:
            validation_failed_message += "Score is a convert"
        
        elif score.has_illegal_mods():
            validation_failed_message += "Score contains disallowed mods. The only allowed mods are: " + create_str_of_allowed_mods()
        
        elif score.has_illegal_dt_ht_rates():
            validation_failed_message += "DT/NC must be set to x1.5 speed, and HT/DC must be set to x0.75 speed"
        
        if await score.is_already_submitted() or score.is_convert or score.has_illegal_mods() or score.has_illegal_dt_ht_rates():
            
            # It's a choice, so we need to access the value (Choice[int] is true-like)
            if display_each_score.value:
                await webhook.send(validation_failed_message)
                
            # The score is not valid regardless of whether it is displayed
            return False
        
        return True
    
    async def add_score_to_database(self, conn: aiosqlite.Connection, score: Score):
        query = "INSERT INTO submitted_scores VALUES (?, ?, ?, ?)"
        await conn.execute(query, (score.user_osu_id, score.beatmap.id, score.beatmapset.id, score.timestamp))
    
    async def update_user_exp_bars_in_database(self, conn: aiosqlite.Connection, score: Score):
        user_exp_bars = await get_user_exp_bars(discord_id=score.user_discord_id)
        
        # Update user_exp_bars with new the new exp values
        for exp_bar_name, amount_of_exp_gained in score.exp_gained.items():
            if amount_of_exp_gained > 0:
                user_exp_bars[exp_bar_name].add_exp_to_expbar(amount_of_exp_gained)
        
        # Write to db
        cursor = await conn.cursor()
        for exp_bar_name, exp_bar in user_exp_bars.items():
            query = f"UPDATE exp_table SET {exp_bar_name.lower()}_exp=?, {exp_bar_name.lower()}_level=? WHERE osu_id=?"
            await cursor.execute(query, (exp_bar.total_exp, exp_bar.level, score.user_osu_id))
    
    async def display_one_score(self, webhook: discord.Webhook, score: Score):
        embed = discord.Embed()
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
        
        # If they quit out, there's no point in telling them they failed
        if not score.is_pass and score.is_complete_runthrough_of_map():
            score_stats += " ▸ Failed"
        
        # Put the metadata in "value", since you can't use markdown syntax to link url in the name part of a field
        text = metadata + '\n' + score_stats
        embed.add_field(name='', value=text, inline=False)
    
    async def add_updated_user_exp_to_embed(self, embed: discord.Embed, score: Score):
        user_exp_bars = await get_user_exp_bars(discord_id=score.user_discord_id)
        
        if not score.is_complete_runthrough_of_map():
            map_completion_percentage = score.map_completion_progress() * 100
            embed.add_field(name=f"EXP Penalty: Restared / Quit out ({map_completion_percentage:.2f}% completed)", value='', inline=False)
        
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