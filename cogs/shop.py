import inspect

import discord
import other.utility
from discord import app_commands
from discord.ext import commands
from other.global_constants import *


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="shop", description="Buy upgrades here!")
    @other.utility.is_verified()
    async def shop(self, interaction: discord.Interaction):
        embed = await self.create_shop_embed(interaction)
        await interaction.response.send_message(embed=embed)

    async def create_shop_embed(self, interaction: discord.Interaction):
        user_currency = await other.utility.get_user_currency(discord_id=interaction.user.id)
        user_upgrades = await other.utility.get_user_upgrades(discord_id=interaction.user.id)
        
        embed = discord.Embed(title="Shop")
        embed.add_field(name="Purse:", value=other.utility.create_str_of_user_currency(user_currency), inline=False)
        self.populate_shop_embed_with_upgrades(user_upgrades, embed)
        return embed

    def populate_shop_embed_with_upgrades(self, user_upgrades: dict[str, int], embed: discord.Embed):
        for upgrade_id, upgrade in upgrade_manager.upgrades.items():
            upgrade_name = upgrade.name
            current_upgrade_level = user_upgrades[upgrade_id]
            max_level = upgrade.max_level
            next_upgrade_level_cost = upgrade.cost(current_upgrade_level+1)
            currency_emoji = ANIMATED_CURRENCY_UNIT_EMOJIS[upgrade.cost_currency_unit]
            upgrade_description = upgrade.description
            
            if current_upgrade_level == max_level:
                text = f"""
                        **{upgrade_name} [Level {current_upgrade_level}/{max_level}]**
                        {upgrade_description}\n
                        """
                
            else:
                text = f"""
                        **{upgrade_name} [Level {current_upgrade_level}/{max_level}]** - {next_upgrade_level_cost} {currency_emoji}
                        {upgrade_description}
                        (Purchase with `/buy {upgrade_id}`)
                        """

            text = inspect.cleandoc(text)
            embed.add_field(name='', value=text, inline=False)
    
    @app_commands.command(name="buy", description="Use this to buy upgrades and items!")
    @app_commands.describe(times_to_purchase="How many times you want to buy it. Leave blank to buy 1. Enter a high number to buy max.")
    @other.utility.is_verified()
    async def buy(self, interaction: discord.Interaction, thing_to_purchase_id: str, times_to_purchase: int = 1):
        if thing_to_purchase_id in upgrade_manager.upgrades.keys():
            await upgrade_manager.process_upgrade_purchase(interaction, thing_to_purchase_id, times_to_purchase)
        else:
            await interaction.response.send_message("The thing you're trying to buy can't be found!")
        
        # Display shop again after using the command
        embed = await self.create_shop_embed(interaction)
        await interaction.followup.send(embed=embed)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(ShopCog(bot))