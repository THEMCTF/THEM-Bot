import asyncio
import datetime
import json
import os

import disnake
import google.auth
import yaml
from disnake import TextInputStyle
from disnake.ext import commands, tasks
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Modules.Logger import logger


class ActiveCTF(commands.Cog):
    def __init__(self, bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.admin_user_ids = config.get("admin_user_ids", [])
        
        # Configure the logger
        logger.configure(bot, config)

    async def chalname_autocompleter(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        """Autocomplete for challenge names."""
        challenges = await self.db.read_table("challenges")
        return [chal for chal in challenges if user_input.lower() in chal.lower()]

    @commands.slash_command(
        name="submitflag", description="Submit a flag for the current CTF"
    )
    @logger
    async def submit_flag(
        self,
        inter: disnake.ApplicationCommandInteraction,
        flag: str,
        chalname: str = commands.Param(autocomplete=chalname_autocompleter),
    ):
        await inter.response.send_message(
            f"Flag submitted: `{flag}` for challenge: **{chalname}**"
        )


def setup(bot):
    bot.add_cog(ActiveCTF(bot, bot.db, bot.config))
