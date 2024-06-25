import os

import discord
from classes.http_session import HttpSession
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

ALLOWED_MODS: list[str] = ['NF', 'EZ', 'HD', 'HR', 'FL', 'DT', 'NC', 'HT', 'DC', 'SD', 'PF', 'CL', 'AC', 'SG', 'MU']  # DT+NC, HT+DC
EXP_BAR_NAMES: list[str] = ['Overall', 'NM', 'HD', 'HR', 'DT', 'HT']  # Warning: Does not include NC, DC

osu_api = OssapiAsync(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(), activity=discord.CustomActivity(name="🥁 banging your mother 🥁"), help_command=None)
http_session = HttpSession()