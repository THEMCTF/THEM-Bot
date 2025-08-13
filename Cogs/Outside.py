import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class OutsideCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="ping", description="Returns websocket latency.")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        latency_ms = round(self.bot.latency * 1000, 2)
        await inter.response.send_message(f"Pong! Latency is **`{latency_ms}`ms**.")
        await Logger.log_action(
            self,
            text=f"**/ping** was ran",
            color=disnake.Colour.red(),
            type="Outside",
            user=inter.author,
        )


def setup(bot):
    bot.add_cog(OutsideCog(bot))
