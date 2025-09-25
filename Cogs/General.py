# import json

import os
import time

import disnake
from disnake.ext import commands

from Modules import log
from Modules.CooldownManager import dynamic_cooldown


class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @log(text="Ping command was used", color=0x00FF00)
    @commands.slash_command(name="ping", description="Check bot latency and uptime")
    @dynamic_cooldown()
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        # Create container
        container = disnake.ui.View()

        # Calculate initial metrics
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

        # Create embeds for different sections
        status_embed = disnake.Embed(title="Bot Status", color=disnake.Color.green())
        status_embed.add_field(
            name="API Latency", value=f"{api_latency}ms", inline=True
        )
        status_embed.add_field(
            name="WebSocket Latency", value=f"{websocket_latency}ms", inline=True
        )
        status_embed.add_field(name="Uptime", value=uptime_str, inline=False)

        # Add refresh button
        refresh_button = disnake.ui.Button(
            style=disnake.ButtonStyle.green, label="Refresh", custom_id="refresh_ping"
        )
        container.add_item(refresh_button)

        # Send initial message with embed and button
        await inter.followup.send(embed=status_embed, view=container)

    @commands.Cog.listener("on_button_click")
    async def ping_button_handler(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "refresh_ping":
            return

        # Calculate new metrics
        api_latency = round(self.bot.latency * 1000)
        websocket_latency = round(self.bot.latency * 1000)

        current_time = time.time()
        uptime = current_time - self.bot.launch_time
        days = int(uptime // (24 * 3600))
        hours = int((uptime % (24 * 3600)) // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # Update embed
        status_embed = disnake.Embed(title="Bot Status", color=disnake.Color.green())
        status_embed.add_field(
            name="API Latency", value=f"{api_latency}ms", inline=True
        )
        status_embed.add_field(
            name="WebSocket Latency", value=f"{websocket_latency}ms", inline=True
        )
        status_embed.add_field(name="Uptime", value=uptime_str, inline=False)

        # Update message with new embed
        await inter.response.edit_message(embed=status_embed)

    @log(text="Gif command was used", color=0xFF0000)
    @commands.slash_command(name="gif", description="gif.")
    @dynamic_cooldown()
    async def gif(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            "https://tenor.com/view/them-ctf-scream-scream-if-you-love-them-the-rock-gif-5196550339096611233"
        )

    @log(text="Source command was used", color=0x00FF00)
    @commands.slash_command(name="source", description="Sends HER?! source code")
    @dynamic_cooldown()
    async def source(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("https://github.com/THEMCTF/THEM-Bot")

    @log(text="Them counter command was used", color=0x00FF00)
    @commands.slash_command(
        name="themcount", description="Shows how many times THEM has been summoned"
    )
    @dynamic_cooldown()
    async def them_count(self, inter: disnake.ApplicationCommandInteraction):
        from Modules.Database import Database

        count = await Database.get_them_counter()
        await inter.response.send_message(
            f"THEM has been summoned **{count:,}** times!", ephemeral=False
        )

    @log()
    @commands.slash_command(name="help", description="List all slash commands.")
    @dynamic_cooldown()
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
