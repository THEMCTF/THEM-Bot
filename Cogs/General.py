# import json

import time

import disnake
from disnake.ext import commands

from Modules import log


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="test", description="test.")
    async def test(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("YOOOO")
        await Logger.log_action(
            self,
            text=f"**/test** was ran",
            color=disnake.Colour.red(),
            type="General",
            user=inter.author,
        )

    @commands.slash_command(name="gif", description="gif.")
    async def gif(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            "https://cdn.discordapp.com/attachments/1382763557816500227/1400565040100409405/5NHcc2CSekZ0u3Cb8cVYKCbvDwGz3O372m9bteYZvljpiaUeyaodrWuuML0UK7iDMWilkUkQJR2Pl1xEaOC86BvHHf2RjbJfjWqOStrVYQnxzXEOkT6QzV9nFE7zTuh1TmUh3B74WN9naNsF4wU2tgLHJQ2DtlCcjCwoWrfdZuVMoUiRMp6ZqlWTK3TeHLUDeWlnXi6CuCmHK67geXDD0zh9B5iOiFWxl5fX6OQBPmLdhRpMpItCjnDuxCeCSlItsk9ZU9RALGfmLPFSTBDcE79OTrKanVNJZFHfF74QFrTq839ZYAeNGoEzBInEaC9dgtrlZ2bF640olzMbOx1XB6G9xmyp0ibkSarknXVGiEVPtgDatFrGbo14uZ1x5lZMXlqheNjbq1Bof3JsaL6PD1MpPsVhir6Cjuns4pJl8yWdBHdWKC1xtzLZSH3nKQXAxzNmy8ZFEKBvE2KowiTjgFid0tngNkt0zho1OZ9NJgk7eA8r7VjFQXiB9D1X..gif"
        )
        await Logger.log_action(
            self,
            text=f"**/gif** was ran",
            color=disnake.Colour.red(),
            type="General",
            user=inter.author,
        )

    @commands.slash_command(name="source", description="Sends HER?! source code")
    async def source(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("https://github.com/THEMCTF/THEM-Bot")

    @log()
    @commands.slash_command(name="help", description="List all slash commands.")
    async def help_slash(self, inter: disnake.ApplicationCommandInteraction):
        help_text = "Available slash commands:\n"
        for cmd in self.bot.application_commands:
            help_text += f"/{cmd.name}: {cmd.description}\n"
        await inter.response.send_message(help_text, ephemeral=True)


def setup(bot):
    bot.add_cog(GeneralCog(bot))
