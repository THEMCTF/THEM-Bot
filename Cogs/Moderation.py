# import json

import time

import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="purge", description="purgey purgey")
    async def purge(self, inter: disnake.ApplicationCommandInteraction, time):
        await inter.response.send_message("YOOOO")
        await Logger.log_action(
            self,
            text=f"**/purge** was ran with the content: *{time}*",
            color=disnake.Colour.red(),
            type="Moderation",
            user=inter.author,
        )


def setup(bot):
    bot.add_cog(ModerationCog(bot))
