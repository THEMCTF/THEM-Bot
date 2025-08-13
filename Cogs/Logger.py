import asyncio
import os
from time import time

import disnake
import json5
from disnake.ext import commands
from rich import print
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

# Load LOGGING_CHANNEL from a JSON file
with open("/Users/starry/Desktop/Code/THEMc/bot/config.json5", "r") as f:
    data = json5.load(f)
    LOGGING_CHANNEL = data.get("LOGGING_CHANNEL", [])


class LoggerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, text, color, type):
        channel = self.bot.get_channel(LOGGING_CHANNEL)
        if channel:
            await channel.send(f"{text}")
        else:
            print(
                f"[red]Error:[/red] Logger channel with ID {LOGGING_CHANNEL} not found."
            )


def setup(bot):
    bot.add_cog(LoggerCog(bot))
