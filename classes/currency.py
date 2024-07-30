from enum import auto

from classes.extended_enum import ExtendedEnum


class CurrencyID(ExtendedEnum):
    taiko_tokens = auto()

class Currency:
    currency_id: CurrencyID
    discord_emoji: str
    animated_discord_emoji: str
    
    def __init__(self, currency_id: CurrencyID, discord_emoji: str, animated_discord_emoji: str):
        self.currency_id = currency_id
        self.discord_emoji = discord_emoji
        self.animated_discord_emoji = animated_discord_emoji
    
def get_all_currencies() -> dict[str, Currency]:
    """Returns a dict with the currency id as the key, and its Currency object as the value."""
    
    currencies = {}
    currencies['taiko_tokens'] = Currency(
        currency_id = CurrencyID.taiko_tokens,
        discord_emoji = "<:taiko_tokens:1259156904349794357>",
        animated_discord_emoji = "<a:taiko_tokens_spinning:1259859321475305504>",
    )
    
    return currencies