import asyncio
import sys
import time

import disnake
import humanize
import yaml
from disnake.ext import commands

from Modules.Logger import logger


class GeneralCog(commands.Cog):

    def __init__(self, bot, db, config, launch_time):
        self.bot = bot
        self.db = db
        self.config = config
        self.launch_time = launch_time
        self.admin_user_ids = config.get("admin_user_ids", [])
        self.shutdown_emoji = config.get("shutdown_emoji", "🔴")

        # Configure the logger
        logger.configure(bot, config)

    async def cog_load(self):
        """A special method that is called when the cog is loaded."""
        print("Loading GeneralCog...")
        # Find the shutdown command and dynamically update its guild_ids
        # This is necessary because guild_ids cannot be a callable.
        shutdown_cmd = self.bot.get_slash_command("shutdown")
        if shutdown_cmd and self.config.get("guild_id"):
            shutdown_cmd.guild_ids = [self.config.get("guild_id")]
        print("GeneralCog loaded.")

    # --- Slash Commands ---
    @commands.slash_command(
        name="ping",
        description="Check bot latency and uptime.",
    )
    @logger
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        # measure API latency by deferring response so we see the time taken
        start_time = time.perf_counter()
        await inter.response.defer()
        end_time = time.perf_counter()
        api_latency = round((end_time - start_time) * 1000)
        websocket_latency = round(self.bot.latency * 1000)

        # find uptime
        uptime_seconds = int(time.time() - self.launch_time)
        uptime_str = humanize.precisedelta(uptime_seconds, minimum_unit="seconds")

        # make container
        container = disnake.ui.Container(
            *(
                disnake.ui.TextDisplay(content="## Bot Status"),
                disnake.ui.Separator(
                    divider=True, spacing=disnake.SeparatorSpacing.large
                ),
                disnake.ui.TextDisplay(content=f"API Latency: {api_latency}ms"),
                disnake.ui.TextDisplay(
                    content=f"WebSocket Latency: {websocket_latency}ms"
                ),
                disnake.ui.TextDisplay(content=f"Uptime: {uptime_str}"),
            )
        )

        await inter.followup.send(components=container)

    @commands.slash_command(name="gif", description="gif.")
    # @logger(message="hi")
    async def gif(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(
            "https://tenor.com/view/them-ctf-scream-scream-if-you-love-them-the-rock-gif-5196550339096611233"
        )

    @commands.slash_command(name="source", description="Sends HER?! source code")
    # @logger
    async def source(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message("https://github.com/THEMCTF/THEM-Bot")

    @commands.slash_command(
        name="themcount", description="Shows how many times THEM?! has been mentioned"
    )
    # @logger
    async def them_count(self, inter: disnake.ApplicationCommandInteraction):
        times_rows = await self.db.find_rows("random", "key", "them_count")
        if times_rows:
            times_summoned = await self.db.read_table(
                "random", start_row=times_rows[0]["id"], start_col=1
            )
            await inter.response.send_message(
                f"THEM has been summoned **{times_summoned}** times!", ephemeral=False
            )
        else:
            await inter.response.send_message(
                "Could not find the number of times THEM has been summoned.",
                ephemeral=True,
            )

    @commands.slash_command(name="help", description="List all slash commands.")
    # @logger
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
    # @logger
    async def shutdown_command(self, inter: disnake.ApplicationCommandInteraction):
        """Gracefully shutdown the bot via Discord command"""
        await inter.response.send_message(
            f"{self.shutdown_emoji} Shutting down bot...", ephemeral=True
        )
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
    bot.add_cog(GeneralCog(bot, bot.db, bot.config, bot.launch_time))
