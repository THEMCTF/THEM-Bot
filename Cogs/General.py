# import json

import os
import time

import disnake
from disnake.ext import commands

from Modules import log


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @log(text="Ping command was used", color=0x00FF00)
    @commands.slash_command(name="ping", description="Check bot latency and uptime")
    @commands.cooldown(1, 5, commands.BucketType.user)  # 1 use per 5 seconds per user
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        # Calculate various metrics
        start_time = time.perf_counter()
        await inter.response.defer()
        end_time = time.perf_counter()

        api_latency = round((end_time - start_time) * 1000)
        websocket_latency = round(self.bot.latency * 1000)

        # Calculate uptime
        current_time = time.time()
        uptime = current_time - self.bot.launch_time

        days = int(uptime // (24 * 3600))
        hours = int((uptime % (24 * 3600)) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # Create a fancy message with unicode blocks
        message = (
            "```ansi\n"
            "\033[1;32mBot Status\033[0m\n"
            "├─ \033[1;34mPing\033[0m\n"
            f"│  ├─ API: {api_latency}ms\n"
            f"│  └─ WebSocket: {websocket_latency}ms\n"
            "└─ \033[1;35mUptime\033[0m\n"
            f"   └─ {uptime_str}\n"
            "```"
        )

        await inter.followup.send(message)

    @log(text="Changelog command was used", color=0x00FF00)
    @commands.slash_command(
        name="changelog", description="Get recent changes and manage notifications"
    )
    async def changelog(self, inter: disnake.ApplicationCommandInteraction):
        # Create buttons for subscribing/unsubscribing
        subscribe_button = disnake.ui.Button(
            style=disnake.ButtonStyle.green,
            label="Subscribe to Updates",
            custom_id="changelog_subscribe",
        )
        unsubscribe_button = disnake.ui.Button(
            style=disnake.ButtonStyle.red,
            label="Unsubscribe",
            custom_id="changelog_unsubscribe",
        )

        # Create action row with buttons
        components = disnake.ui.ActionRow(subscribe_button, unsubscribe_button)

        # Get changelog content
        changelog_path = os.path.join(os.path.dirname(__file__), "../changelog.md")
        with open(changelog_path, "r") as f:
            content = f.read()

        # Format message
        message = f"```md\n{content}\n```\n\n*Click the buttons below to manage changelog notifications*"

        await inter.response.send_message(message, components=components)

    @commands.Cog.listener("on_button_click")
    async def changelog_button_handler(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("changelog_"):
            return

        from Modules.Database import Database

        if inter.component.custom_id == "changelog_subscribe":
            success = await Database.add_changelog_subscriber(inter.author.id)
            if success:
                await inter.response.send_message(
                    "You've been subscribed to changelog notifications! You'll receive a DM when changes are made.",
                    ephemeral=True,
                )
            else:
                await inter.response.send_message(
                    "Failed to subscribe you to notifications. Please try again later.",
                    ephemeral=True,
                )

        elif inter.component.custom_id == "changelog_unsubscribe":
            success = await Database.remove_changelog_subscriber(inter.author.id)
            if success:
                await inter.response.send_message(
                    "You've been unsubscribed from changelog notifications.",
                    ephemeral=True,
                )
            else:
                await inter.response.send_message(
                    "Failed to unsubscribe you from notifications. Please try again later.",
                    ephemeral=True,
                )

    @log(text="Gif command was used", color=0xFF0000)
    @commands.slash_command(name="gif", description="gif.")
    @commands.cooldown(1, 10, commands.BucketType.user)  # 1 use per 10 seconds per user
    async def gif(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            "https://cdn.discordapp.com/attachments/1382763557816500227/1400565040100409405/5NHcc2CSekZ0u3Cb8cVYKCbvDwGz3O372m9bteYZvljpiaUeyaodrWuuML0UK7iDMWilkUkQJR2Pl1xEaOC86BvHHf2RjbJfjWqOStrVYQnxzXEOkT6QzV9nFE7zTuh1TmUh3B74WN9naNsF4wU2tgLHJQ2DtlCcjCwoWrfdZuVMoUiRMp6ZqlWTK3TeHLUDeWlnXi6CuCmHK67geXDD0zh9B5iOiFWxl5fX6OQBPmLdhRpMpItCjnDuxCeCSlItsk9ZU9RALGfmLPFSTBDcE79OTrKanVNJZFHfF74QFrTq839ZYAeNGoEzBInEaC9dgtrlZ2bF640olzMbOx1XB6G9xmyp0ibkSarknXVGiEVPtgDatFrGbo14uZ1x5lZMXlqheNjbq1Bof3JsaL6PD1MpPsVhir6Cjuns4pJl8yWdBHdWKC1xtzLZSH3nKQXAxzNmy8ZFEKBvE2KowiTjgFid0tngNkt0zho1OZ9NJgk7eA8r7VjFQXiB9D1X..gif"
        )

    @log(text="Source command was used", color=0x00FF00)
    @commands.slash_command(name="source", description="Sends HER?! source code")
    @commands.cooldown(1, 30, commands.BucketType.user)  # 1 use per 30 seconds per user
    async def source(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("https://github.com/THEMCTF/THEM-Bot")

    @log()  # fucking hell
    @commands.slash_command(name="help", description="List all slash commands.")
    async def help_slash(self, inter: disnake.ApplicationCommandInteraction):
        help_text = "Available slash commands:\n"
        for cmd in self.bot.application_commands:
            help_text += f"/{cmd.name}: {cmd.description}\n"
        await inter.response.send_message(help_text, ephemeral=True)


def setup(bot):
    bot.add_cog(GeneralCog(bot))
