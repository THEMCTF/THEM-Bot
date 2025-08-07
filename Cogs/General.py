# import json

import disnake
from disnake.ext import commands


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="test", description="test.")
    async def test(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("YOOOO")
        print(f"\033[34m{inter.author.display_name} just ran /test\033[0m")

    @commands.slash_command(name="help", description="List all slash commands.")
    async def help_slash(self, inter: disnake.ApplicationCommandInteraction):
        help_text = "Available slash commands:\n"
        for cmd in self.bot.application_commands:
            help_text += f"/{cmd.name}: {cmd.description}\n"
        await inter.response.send_message(help_text, ephemeral=True)
        print(f"\033[34m{inter.author.display_name} just ran /help\033[0m")


def setup(bot):
    bot.add_cog(GeneralCog(bot))
