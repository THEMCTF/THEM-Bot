# import json

import os
import time

import disnake
from disnake.ext import commands

from Modules.CooldownManager import dynamic_cooldown
from Modules.Logger import Logger


class PingView(disnake.ui.View):
    def __init__(self, bot, *, initial_api_latency: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.api_latency = initial_api_latency

    def _get_content(self, api_latency: int) -> str:
        """Generates the content for the ping message."""
        # Calculate uptime
        uptime = time.time() - self.bot.launch_time
        days = int(uptime // (24 * 3600))
        hours = int((uptime % (24 * 3600)) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        websocket_latency = round(self.bot.latency * 1000)

        return f"""
        **Bot Status**
        WebSocket Latency: {websocket_latency}ms
        API Latency: {api_latency}ms
        Uptime: {uptime_str}
        """

    @disnake.ui.button(
        label="Refresh", style=disnake.ButtonStyle.green, custom_id="refresh_ping"
    )
    async def refresh_button(
        self, _button: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        """Callback for the refresh button."""
        start_time = time.perf_counter()
        await inter.response.defer()
        api_latency = round((time.perf_counter() - start_time) * 1000)

        content = self._get_content(api_latency=api_latency)
        await inter.edit_original_message(content=content)


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="ping", description="Check bot latency and uptime")
    @Logger
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        """Shows bot latency and uptime."""
        # Perform initial API latency check
        start_time = time.perf_counter()
        await inter.response.defer()
        api_latency = round((time.perf_counter() - start_time) * 1000)

        # Create the view and the initial message content
        view = PingView(self.bot, initial_api_latency=api_latency)
        content = view._get_content(api_latency=api_latency)
        await inter.followup.send(content, view=view)

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
        from Modules.Database import Database

        count = await Database.get_them_counter()
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
