import os
import re
import typing
from typing import Any

import aiosqlite
import discord
import other.utility
from classes.currency_manager import CurrencyManager
from classes.exp_manager import ExpManager
from classes.score import Score
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from other.global_constants import *


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
    @app_commands.checks.dynamic_cooldown(other.utility.command_cooldown_for_live_bot)
    @other.utility.is_verified()
    async def submit(self, interaction: discord.Interaction, display_each_score: Choice[int], number_of_scores_to_submit: int = 100):
        
        # Slash commands time out after 3 seconds, so we send a response first in case the command takes too long to execute
        await interaction.response.send_message("Finding scores...")
        
        user_exp_bars_before_submission = await other.utility.get_user_exp_bars(discord_id=interaction.user.id)
        user_currency_before_submission = await other.utility.get_user_currency(discord_id=interaction.user.id)
        user_upgrade_levels = await other.utility.get_user_upgrade_levels(discord_id=interaction.user.id)
        
        exp_manager = ExpManager(user_exp_bars_before_submission, user_upgrade_levels)
        currency_manager = CurrencyManager(user_currency_before_submission, user_upgrade_levels)
        webhook = interaction.followup
        
        all_scores = await self.fetch_user_scores(interaction, number_of_scores_to_submit)
        await self.display_num_scores_fetched(interaction, display_each_score, all_scores)
        await self.process_and_display_score_impl(webhook, display_each_score, all_scores, exp_manager, currency_manager)
        await self.display_total_exp_and_currency_change(interaction, webhook, exp_manager, currency_manager)

    async def fetch_user_scores(self, interaction: discord.Interaction, number_of_scores_to_submit: int):
        headers = {
            'Accept': "application/json",
            'Content-Type': "application/json",
            'x-api-version': "20220705",  # get modern score return info
            'Authorization': f"Bearer {os.getenv('OSU_API_ACCESS_TOKEN')}",
        }
        
        user_osu_id = await other.utility.get_osu_id(discord_id=interaction.user.id)
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

    async def process_and_display_score_impl(self, webhook: discord.Webhook, display_each_score: Choice[int], all_scores: list[dict[str, Any]], 
                                             exp_manager: ExpManager, currency_manager: CurrencyManager):
        debug_file = open("./data/scores.txt", "w")
        
        for score_info in all_scores:
                
            score = await Score.create_score_object(score_info)

            if not await self.score_is_valid(webhook, score, display_each_score):
                continue
            
            exp_gained_from_score = await exp_manager.process_one_score(score)
            currency_gained_from_score = await currency_manager.process_one_score(score)
            
            self.write_to_debug_file(debug_file, score, exp_manager, currency_manager)
            
            # update db
            await self.add_score_to_database(score)
            
            if display_each_score.value:
                await self.display_one_score(webhook, score, exp_gained_from_score, currency_gained_from_score, exp_manager, currency_manager)    
            
        debug_file.close()
        await webhook.send("All done!")

    async def display_total_exp_and_currency_change(self, interaction: discord.Interaction, webhook: discord.Webhook, 
                                                    exp_manager: ExpManager, currency_manager: CurrencyManager):
        osu_username = await other.utility.get_osu_username(discord_id=interaction.user.id)
        embed = discord.Embed(title=f"{osu_username}'s EXP and currency changes:")
        embed.colour = discord.Color.from_rgb(255,255,255)  # white
        
        await self.add_total_exp_change_to_embed(embed, exp_manager)
        await self.add_total_currency_change_to_embed(embed, currency_manager)
        
        if len(embed.fields) == 0:
            embed.add_field(name='', value="No change!")
        
        await webhook.send(embed=embed)

    async def add_total_exp_change_to_embed(self, embed: discord.Embed, exp_manager: ExpManager):

        for (exp_bar_name, exp_bar_before), exp_bar_after in zip(exp_manager.initial_user_exp_bars.items(), exp_manager.current_user_exp_bars.values()):
            if exp_bar_after.total_exp > exp_bar_before.total_exp:
                name_info = f"{exp_bar_name} Level {exp_bar_before.level} "
                if exp_bar_after.level > exp_bar_before.level:
                    name_info += f"→ {exp_bar_after.level} (+{exp_bar_after.level - exp_bar_before.level})"
                
                value_info = f"EXP: {exp_bar_before.total_exp} → {exp_bar_after.total_exp} (+{exp_bar_after.total_exp - exp_bar_before.total_exp})"
                
                embed.add_field(name=name_info, value=value_info, inline=False)
        
    async def add_total_currency_change_to_embed(self, embed: discord.Embed, currency_manager: CurrencyManager):
        for (currency_id, currency_amount_before), currency_amount_after in zip(currency_manager.initial_user_currency.items(), currency_manager.current_user_currency.values()):
            if currency_amount_after > currency_amount_before:
                value_info = f"{ALL_CURRENCIES[currency_id].animated_discord_emoji}: {currency_amount_before} → {currency_amount_after} (+{currency_amount_after - currency_amount_before})"
                embed.add_field(name='', value=value_info, inline=False)
                
    def write_to_debug_file(self, file: typing.TextIO, score: Score, exp_manager: ExpManager, currency_manager: CurrencyManager):
        """For debugging purposes."""
        
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
        for item in exp_manager.debug_log:
            file.write(f"{item}\n")
        
        file.write("\nCURRENCY\n")
        for item in currency_manager.debug_log:
            file.write(f"{item}\n")
        
        file.write("\n"*5)

    async def score_is_valid(self, webhook: discord.Webhook, score: Score, display_each_score: Choice[int]) -> bool:
        validation_failed_message = f"Ignoring **{score.beatmapset.artist} - {score.beatmapset.title} [{score.beatmap.difficulty_name}]**\n"
        validation_failed_message += "Reason: "
        
        # Initialize string and append reason if applicable
        validation_failed_reason = ""
        
        if await score.is_already_submitted():
            validation_failed_reason = "Score is already submitted"
        
        elif score.is_afk():
            validation_failed_reason = "You AFKed while playing"
        
        elif score.has_illegal_mods():
            validation_failed_reason = "Score contains disallowed mods. The only allowed mods are: " + other.utility.create_str_of_allowed_mods()
        
        elif score.has_illegal_dt_ht_rates():
            validation_failed_reason = "DT/NC must be set to x1.5 speed, and HT/DC must be set to x0.75 speed"
        
        # If the reason is not empty, send the validation failed message
        if validation_failed_reason:
            validation_failed_message += validation_failed_reason
            
            # display_each_score is type Choice, so we need to access the value
            if display_each_score.value:
                await webhook.send(validation_failed_message)
                
            # The score is not valid regardless of whether it is displayed
            return False
        
        return True

    async def add_score_to_database(self, score: Score):
        async with aiosqlite.connect("./data/database.db") as conn:
            query = "INSERT INTO submitted_scores VALUES (?, ?, ?, ?)"
            await conn.execute(query, (score.user_osu_id, score.beatmap.id, score.beatmapset.id, score.timestamp))
            await conn.commit()
    
    async def display_one_score(self, webhook: discord.Webhook, score: Score, exp_gained_from_score: dict[str, int], currency_gained_from_score: dict[str, int], 
                                exp_manager: ExpManager, currency_manager: CurrencyManager):
        embed = discord.Embed()
        embed.title = f"{score.username} submitted a new score:"
        await self.add_metadata_and_score_stats_to_embed(embed, score)
        await self.add_updated_user_exp_to_embed(embed, score, exp_gained_from_score, exp_manager)
        await self.add_updated_currency_to_embed(embed, currency_gained_from_score, currency_manager)
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
    
    async def add_updated_user_exp_to_embed(self, embed: discord.Embed, score: Score, exp_gained_from_score: dict[str, int], exp_manager: ExpManager):
        if not score.is_complete_runthrough_of_map():
            map_completion_percentage = score.map_completion_progress() * 100
            embed.add_field(name=f"EXP Penalty: Restared / Quit out ({map_completion_percentage:.2f}% completed)", value='', inline=False)
        
        for exp_bar_name, exp_gained in exp_gained_from_score.items():
            if exp_gained > 0:
                level = exp_manager.current_user_exp_bars[exp_bar_name].level
                exp_progress_to_next_level = exp_manager.current_user_exp_bars[exp_bar_name].exp_progress_to_next_level
                exp_required_for_next_level = exp_manager.current_user_exp_bars[exp_bar_name].exp_required_for_next_level
                
                embed_name = f"{exp_bar_name} Level {level}"
                embed_value = f"{exp_progress_to_next_level}/{exp_required_for_next_level} **(+{exp_gained})**"
                
                embed.add_field(name=embed_name, value=embed_value)
    
    async def add_updated_currency_to_embed(self, embed: discord.Embed, currency_gained_from_score: dict[str, int], currency_manager: CurrencyManager):
        for currency_name, currency_gain in currency_gained_from_score.items():
            if currency_gain > 0:
                embed.add_field(name=f"{other.utility.prettify_currency_db_name(currency_name)}: {currency_manager.current_user_currency[currency_name]} (+{currency_gain})", value='', inline=False)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(SubmitCog(bot))