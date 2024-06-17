import discord
from ossapi import OssapiAsync
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="./data/sensitive.env", verbose=True)

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
BOT_ID: int = int(os.environ["BOT_ID"])
OSU_CLIENT_SECRET: str = os.environ["OSU_CLIENT_SECRET"]
OSU_CLIENT_ID: int = int(os.environ["OSU_CLIENT_ID"])
OSU_API_KEY: str = os.environ["OSU_API_KEY"]  # Legacy API

JARVIS_ID = 208433054572740608  # (That's me!)

ADMIN_ID_LIST: list[int] = [208433054572740608]  # jarvisgaming

ALLOWED_REPLAY_MODS: list[str] = ['NF', 'EZ', 'HD', 'HR', 'FL', 'SD', 'PF', 'ScoreV2']
EXP_BAR_NAMES: list[str] = ['Overall', 'NM', 'HD', 'HR']

osu_api = OssapiAsync(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all(), activity=discord.CustomActivity(name="🥁 banging your mother 🥁"), help_command=None)