# import json

import os
import time

import disnake
import yaml
from disnake.ext import commands

from Modules.CooldownManager import dynamic_cooldown
from Modules.Logger import Logger


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="gif", description="gif.")
    @Logger
    async def gif(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            "https://tenor.com/view/them-ctf-scream-scream-if-you-love-them-the-rock-gif-5196550339096611233"
        )

    @commands.slash_command(name="source", description="Sends HER?! source code")
    @Logger
    async def source(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("https://github.com/THEMCTF/THEM-Bot")

    @commands.slash_command(
        name="themcount", description="Shows how many times THEM?! has been mentioned"
    )
    @Logger
    async def them_count(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            f"THEM has been summoned **{count:,}** times!", ephemeral=False
        )

    @commands.slash_command(name="help", description="List all slash commands.")
    @Logger
    async def help_slash(self, inter: disnake.ApplicationCommandInteraction):
        """Shows all available commands"""
        help_text = "```\nAvailable Commands:\n"

        # Group commands by cog
        cog_commands = {}

        for cmd in self.bot.application_commands:
            if isinstance(
                cmd, (commands.InvokableSlashCommand, commands.SubCommandGroup)
            ):
                cog_name = cmd.cog_name or "No Category"
                if cog_name not in cog_commands:
                    cog_commands[cog_name] = []
                # Get description, fallback to command name if no description
                desc = getattr(cmd, "description", "") or "No description available"
                cog_commands[cog_name].append(f"/{cmd.name}: {desc}")

        # Format and add each category
        for cog_name, cmds in sorted(cog_commands.items()):
            if cmds:  # Only show categories that have commands
                help_text += f"\n{cog_name}:\n"
                for cmd in sorted(cmds):
                    help_text += f"  {cmd}\n"

        help_text += "```"
        await inter.response.send_message(help_text, ephemeral=True)


def setup(bot):
    bot.add_cog(GeneralCog(bot))
