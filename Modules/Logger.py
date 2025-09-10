import asyncio
import datetime
import os
from time import time

import disnake
import json5
from disnake.ext import commands

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Go one folder up and join with config.json5
config_path = os.path.join(current_dir, "..", "config.json5")

# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    data = json5.load(f)  # make this use yml later
    LOGGING_CHANNEL = data.get("LOGGING_CHANNEL", [])
    ENABLE_CHANNEL_LOGGING = data.get("ENABLE_CHANNEL_LOGGING", [])
    ENABLE_LOG_TO_FILE = data.get("ENABLE_LOG_TO_FILE", [])


class Logger:
    def __init__(self, bot):
        self.bot = bot
        self.rendition = 0  # this words just sounds cool, it's not really related -starry [9/10/2025]

    async def __call__(self, text, color, type, priority, user=None):
        if ENABLE_LOG_TO_FILE == True:
            # TODO: write code to log the message like: [{date}] {user} {message}  to a txt file with a new line for every message
        if ENABLE_CHANNEL_LOGGING == False:
            print(f"{type}: {text}; {user}")
            return
        if priority < self.rendition:
            return
        channel = self.bot.get_channel(LOGGING_CHANNEL)
        if channel:
            embed = disnake.Embed(
                description=text,
                color=color,
                timestamp=datetime.datetime.now(),
            )
            embed.set_footer(text=type)
            if user != None:
                embed.set_author(
                    name=user.display_name,
                    icon_url=user.display_avatar,
                )

            await channel.send(embed=embed)
        else:
            print(
                f"[red]Error:[/red] Logger channel with ID {LOGGING_CHANNEL} not found."
            )
