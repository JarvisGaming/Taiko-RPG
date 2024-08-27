from typing import TYPE_CHECKING

from classes.buff_effect import BuffEffect, BuffEffectType
from classes.upgrade import Upgrade
from other.global_constants import NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN

if TYPE_CHECKING:
    from classes.exp import ExpBar
    from classes.score import Score

def init_upgrades() -> dict[str, Upgrade]:
    """Returns a dict containing all the upgrades in the game. Upgrade IDs are used as the key, and the individual upgrades are used as the value."""
    
    all_upgrades = {}
        
    def exp_length_bonus_effect(upgrade_level: int, score: "Score", exp_bar_exp_gain: dict[str, int]):
        if score.is_complete_runthrough_of_map():
            drain_time_minutes = score.beatmap.drain_time // 60
            exp_bar_exp_gain['Overall'] += (upgrade_level * drain_time_minutes)
    
    all_upgrades['exp_length_bonus'] = (Upgrade(
        id = "exp_length_bonus",
        name = "EXP Length Bonus", 
        description = "+1 EXP per minute of drain time per level (applies to maps you've fully completed)",
        max_level = 10, 
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 50 * pow(level, 2),
        effect = BuffEffect.OVERALL_EXP_GAIN,
        effect_type = BuffEffectType.ADDITIVE,
        effect_impl = exp_length_bonus_effect,
    ))
    
    def overall_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int]):
        exp_bar_exp_gain['Overall'] = int(exp_bar_exp_gain['Overall'] * (1 + 0.01 * upgrade_level))
    
    all_upgrades['overall_exp_gain_multiplier'] = (Upgrade(
        id = "overall_exp_gain_multiplier",
        name = "Overall EXP Gain Multiplier", 
        description = "+1% Overall EXP gain per level (additive)",
        max_level = 50,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 15*level,
        effect = BuffEffect.OVERALL_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = overall_exp_gain_multiplier_effect,
    ))
    
    def nm_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['NM'] = int (exp_bar_exp_gain['NM'] * (1 + 0.002 * upgrade_level * user_exp_bars['NM'].level))
    
    all_upgrades['nm_exp_gain_multiplier'] = (Upgrade(
        id = "nm_exp_gain_multiplier",
        name = "NM EXP Gain Multiplier", 
        description = "+0.2% NM EXP gain / NM level, per upgrade level (additive)",
        max_level = 5,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 200 * (level ** 2),
        effect = BuffEffect.NM_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = nm_exp_gain_multiplier_effect,
    ))
    
    def hd_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['HD'] = int (exp_bar_exp_gain['HD'] * (1 + 0.002 * upgrade_level * user_exp_bars['HD'].level))
    
    all_upgrades['hd_exp_gain_multiplier'] = (Upgrade(
        id = "hd_exp_gain_multiplier",
        name = "HD EXP Gain Multiplier", 
        description = "+0.2% HD EXP gain / HD level, per upgrade level (additive)",
        max_level = 5,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 200 * (level ** 2),
        effect = BuffEffect.HD_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = hd_exp_gain_multiplier_effect,
    ))
    
    def hr_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['HR'] = int (exp_bar_exp_gain['HR'] * (1 + 0.002 * upgrade_level * user_exp_bars['HR'].level))
    
    all_upgrades['hr_exp_gain_multiplier'] = (Upgrade(
        id = "hr_exp_gain_multiplier",
        name = "HR EXP Gain Multiplier", 
        description = "+0.2% HR EXP gain / HR level, per upgrade level (additive)",
        max_level = 5,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 200 * (level ** 2),
        effect = BuffEffect.HR_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = hr_exp_gain_multiplier_effect,
    ))
    
    def dt_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['DT'] = int (exp_bar_exp_gain['DT'] * (1 + 0.002 * upgrade_level * user_exp_bars['DT'].level))
    
    all_upgrades['dt_exp_gain_multiplier'] = (Upgrade(
        id = "dt_exp_gain_multiplier",
        name = "DT EXP Gain Multiplier", 
        description = "+0.2% DT EXP gain / DT level, per upgrade level (additive)",
        max_level = 5,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 200 * (level ** 2),
        effect = BuffEffect.DT_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = dt_exp_gain_multiplier_effect,
    ))
    
    def ht_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['HT'] = int (exp_bar_exp_gain['HT'] * (1 + 0.002 * upgrade_level * user_exp_bars['HT'].level))
    
    all_upgrades['ht_exp_gain_multiplier'] = (Upgrade(
        id = "ht_exp_gain_multiplier",
        name = "HT EXP Gain Multiplier", 
        description = "+0.2% HT EXP gain / HT level, per upgrade level (additive)",
        max_level = 5,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: 200 * (level ** 2),
        effect = BuffEffect.HT_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = ht_exp_gain_multiplier_effect,
    ))
    
    def infinite_overall_exp_gain_multiplier_effect(upgrade_level: int, exp_bar_exp_gain: dict[str, int], user_exp_bars: dict[str, "ExpBar"]):
        exp_bar_exp_gain['Overall'] = int(exp_bar_exp_gain['Overall'] * (1 + 0.0002 * upgrade_level * user_exp_bars['Overall'].level))
    
    all_upgrades['infinite_overall_exp_gain_multiplier'] = (Upgrade(
        id = "infinite_overall_exp_gain_multiplier",
        name = "Infinite Overall EXP Gain Multiplier",
        description = f"+0.02% Overall EXP gain / Overall level, per upgrade level (additive)",
        max_level = 10000,
        cost_currency_unit = "taiko_tokens",
        cost = lambda level: int(300 * level ** 1.1),
        effect = BuffEffect.OVERALL_EXP_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = infinite_overall_exp_gain_multiplier_effect,
    ))

    def tt_gain_efficiency_effect(upgrade_level: int, score: "Score", currency_gain: dict[str, int]):
        currency_gain['taiko_tokens'] = score.note_hits // (NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN - upgrade_level)

    all_upgrades['tt_gain_efficiency'] = (Upgrade(
        id = "tt_gain_efficiency",
        name = "Taiko Token Gain Efficiency",
        description = f"-1 note hit needed to gain a Taiko Token. You gain a token every {NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN} hits by default",
        max_level = 20,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: int(10 * pow(1.39, level-1)),
        effect = BuffEffect.TAIKO_TOKEN_GAIN,
        effect_type = BuffEffectType.ADDITIVE,
        effect_impl = tt_gain_efficiency_effect,
    ))
    
    def tt_gain_multiplier_effect(upgrade_level: int, currency_gain: dict[str, int]):
        currency_gain['taiko_tokens'] = int(currency_gain['taiko_tokens'] * (1 + 0.02 * upgrade_level))
    
    all_upgrades['tt_gain_multiplier'] = (Upgrade(
        id = "tt_gain_multiplier",
        name = "Taiko Token Gain Multiplier", 
        description = "+2% Taiko Token gain per level (additive)",
        max_level = 50,
        cost_currency_unit = "taiko_tokens", 
        cost = lambda level: int(25 * pow(1.1, level-1)),
        effect = BuffEffect.TAIKO_TOKEN_GAIN,
        effect_type = BuffEffectType.MULTIPLICATIVE,
        effect_impl = tt_gain_multiplier_effect,
    ))
    
    return all_upgrades