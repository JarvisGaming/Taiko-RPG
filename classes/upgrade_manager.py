import aiosqlite
import discord
import other.utility
from classes.upgrade import Upgrade


class UpgradeManager:

    upgrades: dict[str, Upgrade]  # upgrade_id: upgrade

    def __init__(self):
        self.upgrades = {}
        self.upgrades['exp_length_bonus'] = (Upgrade(
            name = "EXP Length Bonus", 
            description = r"+1 EXP per minute of drain time per level (applies to maps you've fully completed)",
            max_level = 10, 
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 50 * pow(level, 2),
            effect = lambda level, drain_time_minutes: level * drain_time_minutes  # additional EXP gained from upgrade
        ))
        
        self.upgrades['exp_gain_multiplier'] = (Upgrade(
            name = "EXP Gain Multiplier", 
            description = r"+1% EXP gain (additive)",
            max_level = 50,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: 15*level,
            effect = lambda level: 1 + 0.01 * level  # EXP mult from upgrade
        ))
    
        self.upgrades['tt_gain_efficiency'] = (Upgrade(
            name = "Taiko Token Gain Efficiency", 
            description = r"-1 note hit needed to gain a Taiko Token",
            max_level = 20,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: int(10 * pow(1.39, level-1)),
            effect = lambda level: level  # How many less note hits needed per Taiko Token
        ))
        
        self.upgrades['tt_gain_multiplier'] = (Upgrade(
            name = "Taiko Token Gain Multiplier", 
            description = r"+2% Taiko Token gain (additive)",
            max_level = 50,
            cost_currency_unit = "taiko_tokens", 
            cost = lambda level: int(25 * pow(1.1, level-1)),
            effect = lambda level: 1 + 0.02 * level  # Taiko Token mult from upgrade
        ))
    
    def get_upgrade(self, upgrade_id: str) -> Upgrade | None:
        return self.upgrades.get(upgrade_id, None)
    
    async def process_upgrade_purchase(self, interaction: discord.Interaction, upgrade_id: str, times_to_purchase: int):
        await interaction.response.send_message(f"Processing upgrade purchase...")
        
        upgrade = self.get_upgrade(upgrade_id)
        assert upgrade is not None
        upgrade_levels_purchased = 0
        
        for _ in range(times_to_purchase):
            user_currency = await other.utility.get_user_currency(discord_id=interaction.user.id)
            user_upgrades = await other.utility.get_user_upgrades(discord_id=interaction.user.id)
            
            current_upgrade_level = user_upgrades[upgrade_id]
            upgrade_cost = upgrade.cost(user_upgrades[upgrade_id]+1)
            
            if current_upgrade_level >= upgrade.max_level:
                if upgrade_levels_purchased == 0:
                    await interaction.followup.send(f"You already maxed out {upgrade.name}!")
                break
            
            if not await self.user_has_enough_currency(upgrade, user_currency, upgrade_cost):
                if upgrade_levels_purchased == 0:
                    await interaction.followup.send(f"You don't have enough currency to purchase {upgrade.name} (Level {current_upgrade_level+1})!")
                break
            
            await self.update_database_from_purchase(interaction, upgrade_id, upgrade, user_currency, current_upgrade_level, upgrade_cost)
            upgrade_levels_purchased += 1
            
        if upgrade_levels_purchased != 0:
            await interaction.followup.send(f"Purchased {upgrade_levels_purchased} level(s) of {upgrade.name}!")

    async def update_database_from_purchase(self, interaction: discord.Interaction, upgrade_id: str, upgrade: Upgrade, 
                                            user_currency: dict[str, int], current_upgrade_level: int, upgrade_cost: int):
        osu_id = await other.utility.get_osu_id(discord_id=interaction.user.id)
        async with aiosqlite.connect("./data/database.db") as conn:
            # deduct currency
            new_currency_amount = user_currency[upgrade.cost_currency_unit] - upgrade_cost
            await conn.execute(F"UPDATE currency SET {upgrade.cost_currency_unit}=? WHERE osu_id=?", (new_currency_amount, osu_id))
                
            # add level
            new_level = current_upgrade_level + 1
            await conn.execute(F"UPDATE upgrades SET {upgrade_id}=? WHERE osu_id=?", (new_level, osu_id))
                
            await conn.commit()
        

    async def user_has_enough_currency(self, upgrade: Upgrade, user_currency: dict[str, int], upgrade_cost: int):
        if upgrade_cost > user_currency[upgrade.cost_currency_unit]:
            return False
        return True