import disnake
from disnake.ext import commands

from Modules.old.Logger import Logger


class OutsideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="server",
        description="invite link",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    @commands.install_types(user=True)
    @Logger
    async def server(self, inter: disnake.AppCommandInteraction):
        await inter.response.send_message("discord.gg/its-them")

    @commands.slash_command(
        name="the_game",
        description="Don't lose",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    @commands.install_types(user=True)
    @Logger
    async def the_game(self, inter: disnake.AppCommandInteraction, user: disnake.User):
        await inter.response.send_message(f"hey {user.display_name} you lose the game")


def setup(bot):
    bot.add_cog(OutsideCog(bot))
