import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class OutsideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.install_types(user=True)
    @commands.slash_command(
        name="server",
        description="invite link",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    async def server(self, inter: disnake.AppCommandInteraction):
        await inter.response.send_message("discord.gg/its-them")
        guild_name = inter.guild.name if inter.guild else "Direct Message"
        await Logger.log_action(
            self,
            text=f"**/server** was ran in {guild_name}",
            color=disnake.Colour.red(),
            type="Outside",
            user=inter.author,
        )

    @commands.install_types(user=True)
    @commands.slash_command(
        name="the_game",
        description="Don't lose",
        contexts=disnake.InteractionContextTypes(guild=True, private_channel=True),
    )
    async def the_game(self, inter: disnake.AppCommandInteraction, user: disnake.User):
        await inter.response.send_message(f"hey {user.display_name} you lose the game")
        guild_name = inter.guild.name if inter.guild else "Direct Message"
        await Logger.log_action(
            self,
            text=f"**/the_game** was ran in {guild_name}",
            color=disnake.Colour.red(),
            type="Outside",
            user=inter.author,
        )


def setup(bot):
    bot.add_cog(OutsideCog(bot))
