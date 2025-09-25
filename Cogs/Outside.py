import disnake
from disnake.ext import commands

from Modules import log


class OutsideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.install_types(user=True)
    @log(type="Outside", color=disnake.Colour.red())
    @commands.slash_command(
        name="server",
        description="invite link",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    async def server(self, inter: disnake.AppCommandInteraction):
        await inter.response.send_message("discord.gg/its-them")

    @commands.install_types(user=True)
    @log(type="Outside", color=disnake.Colour.red())
    @commands.slash_command(
        name="the_game",
        description="Don't lose",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    async def the_game(self, inter: disnake.AppCommandInteraction, user: disnake.User):
        await inter.response.send_message(f"hey {user.display_name} you lose the game")


def setup(bot):
    bot.add_cog(OutsideCog(bot))
