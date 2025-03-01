import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from ossapi import OssapiAsync
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

load_dotenv(dotenv_path="./data/sensitive.env", verbose=True, override=True)  # This line applies to the whole process, not just the current script

BOT_TOKEN: str = os.environ['BOT_TOKEN']
BOT_ID: int = int(os.environ['BOT_ID'])
OSU_CLIENT_SECRET: str = os.environ['OSU_CLIENT_SECRET']
OSU_CLIENT_ID: int = int(os.environ['OSU_CLIENT_ID'])
OSU_API_KEY: str = os.environ['OSU_API_KEY']  # Legacy API

NOTE_HITS_REQUIRED_PER_TAIKO_TOKEN: int = 50

osu_api = OssapiAsync(OSU_CLIENT_ID, OSU_CLIENT_SECRET)
bot = commands.Bot(command_prefix="rpg!", intents=discord.Intents.all(), activity=discord.CustomActivity(name="🥁 banging your mother 🥁"), help_command=None)

# Google Cloud (Google Drive)
google_auth = GoogleAuth(settings_file="data/google_cloud_settings.yaml")
google_auth.LocalWebserverAuth(launch_browser=False)  # Creates local webserver and auto handles authentication
google_drive = GoogleDrive(google_auth)

# Stores the Discord IDs of people currently running /submit
users_currently_running_submit_command: set[int] = set()