import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class OutsideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.install_types(user=True)
    @commands.slash_command(name="ping", description="Returns websocket latency.")
    async def ping(self, inter: disnake.AppCommandInteraction):
        latency_ms = round(self.bot.latency * 1000, 2)
        await inter.response.send_message(f"Pong! Latency is `{latency_ms}`**ms**.")
        guild_name = inter.guild.name if inter.guild else "Direct Message"
        await Logger.log_action(
            self,
            text=f"**/ping** was ran in {guild_name}",
            color=disnake.Colour.red(),
            type="Outside",
            user=inter.author,
        )

    @commands.install_types(user=True)
    @commands.slash_command(name="the_game", description="Don't lose")
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
