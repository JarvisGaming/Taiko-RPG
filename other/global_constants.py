import os

import discord
from classes.http_session import HttpSession
from classes.upgrade_manager import UpgradeManager
from discord.ext import commands
from dotenv import load_dotenv
from ossapi import OssapiAsync

load_dotenv(dotenv_path="./data/sensitive.env", verbose=True, override=True)  # This line applies to the whole process, not just the current script

BOT_TOKEN: str = os.environ['BOT_TOKEN']
BOT_ID: int = int(os.environ['BOT_ID'])
OSU_CLIENT_SECRET: str = os.environ['OSU_CLIENT_SECRET']
OSU_CLIENT_ID: int = int(os.environ['OSU_CLIENT_ID'])
OSU_API_KEY: str = os.environ['OSU_API_KEY']  # Legacy API

ADMIN_ID_LIST: list[int] = [208433054572740608]  # jarvisgaming

ALLOWED_MODS: list[str] = ['NF', 'EZ', 'HD', 'HR', 'FL', 'DT', 'NC', 'HT', 'DC', 'SD', 'PF', 'CL', 'AC', 'SG', 'MU']
EXP_BAR_NAMES: list[str] = ['Overall', 'NM', 'HD', 'HR', 'DT', 'HT']  # Warning: Does not include NC, DC

CURRENCY_UNITS: list[str] = ['taiko_tokens']
CURRENCY_UNIT_EMOJIS: dict[str, str] = {'taiko_tokens': f"<:taiko_tokens:1259156904349794357>"}  # <emoji_name:emoji_id>
ANIMATED_CURRENCY_UNIT_EMOJIS: dict[str, str] = {'taiko_tokens': f"<a:taiko_tokens_spinning:1259859321475305504>"}  # <a:emoji_name:emoji_id>

osu_api = OssapiAsync(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(), activity=discord.CustomActivity(name="🥁 banging your mother 🥁"), help_command=None)
http_session = HttpSession()
upgrade_manager = UpgradeManager()