import asyncio
import datetime
import os
from time import time

import disnake
import json5
from disnake.ext import commands

# Load LOGGING_CHANNEL from a JSON file
with open("/Users/starry/Desktop/Code/THEMc/bot/config.json5", "r") as f:
    data = json5.load(f)
    LOGGING_CHANNEL = data.get("LOGGING_CHANNEL", [])
    ENABLE_CHANNEL_LOGGING = data.get("ENABLE_CHANNEL_LOGGING", [])


class Logger:
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, text, color, type, user=None):
        if ENABLE_CHANNEL_LOGGING == False:
            print(f"{type}: {text}; {user}")
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
