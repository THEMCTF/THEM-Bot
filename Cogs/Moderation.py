# import json

import time

import disnake
from disnake.ext import commands


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="purge", description="purgey purgey")
    async def purge(self, inter: disnake.ApplicationCommandInteraction, time):
        await inter.response.send_message("YOOOO")
        print(f"\033[34m{inter.author.display_name} just ran /test\033[0m")


def setup(bot):
    bot.add_cog(ModerationCog(bot))
