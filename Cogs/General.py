import asyncio
import sys

import disnake
import yaml
from disnake.ext import commands

from Modules.Logger import Logger


class GeneralCog(commands.Cog):
    def __init__(self, bot, db, config):
        self.bot = bot
        self.config = config
        self.admin_user_ids = config.get("admin_user_ids", [])

    async def cog_load(self):
        """A special method that is called when the cog is loaded."""
        # Find the shutdown command and dynamically update its guild_ids
        # This is necessary because guild_ids cannot be a callable.
        shutdown_cmd = self.bot.get_slash_command("shutdown")
        if shutdown_cmd and self.config.get("guild_id"):
            shutdown_cmd.guild_ids = [self.config.get("guild_id")]

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
            f"THEM has been summoned **{2}** times!", ephemeral=False
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

    @commands.slash_command(
        name="shutdown",
        description="Safely shut down the bot",
        guild_ids=None,  # We will set this dynamically in __init__
    )
    @commands.check(
        lambda inter: inter.author.id in inter.bot.get_cog("GeneralCog").admin_user_ids
    )
    @Logger
    async def shutdown_command(self, inter: disnake.ApplicationCommandInteraction):
        """Gracefully shutdown the bot via Discord command"""
        await inter.response.send_message("🔴 Shutting down bot...", ephemeral=True)
        print(f"Shutdown initiated by {inter.author} ({inter.author.id})")

        # Give time for the message to send
        await asyncio.sleep(1)

        # This function is defined in main.py, but we can call it via the bot instance
        # if we attach it there. For now, let's assume it's globally accessible or refactor later.
        # A better approach would be to have shutdown logic on the bot class itself.
        # For now, we'll just call bot.close() and exit.
        await self.bot.close()
        sys.exit(0)


def setup(bot):
    bot.add_cog(GeneralCog(bot, bot.db, bot.config))
