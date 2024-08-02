from classes.currency import Currency, CurrencyID


def init_currency() -> dict[str, Currency]:
    """Returns a dict containing all the currency in the game. Currency IDs are used as the key, and the individual currencies are used as the value."""
    
    currencies: dict[str, Currency] = {}
    
    currencies['taiko_tokens'] = Currency(
        currency_id = CurrencyID.taiko_tokens,
        discord_emoji = "<:taiko_tokens:1259156904349794357>",
        animated_discord_emoji = "<a:taiko_tokens_spinning:1259859321475305504>",
    )
    
    return currencies