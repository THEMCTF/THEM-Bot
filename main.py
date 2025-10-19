import asyncio
import os
import sys
import time
from pathlib import Path

import disnake
import yaml
from disnake.ext import commands
from dotenv import load_dotenv

from Modules.Database import Database
from Modules.Logger import logger

# ==================== Setup ====================

BANNER = "\033[32m hi\033[0m"
print(BANNER)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# Load configuration
config_path = Path(__file__).parent / "config.yml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)


# ==================== Bot Class ====================


class HER(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        # Set test_guilds for instant command sync in development
        if config.get("development_mode", False):
            testing_guild = config.get("testing_guild_id")
            if testing_guild:
                kwargs["test_guilds"] = [testing_guild]
                print(
                    f"\033[33m⚠  Development mode: Commands will sync instantly to guild {testing_guild}\033[0m"
                )

        super().__init__(*args, **kwargs)
        self.launch_time = time.time()
        self.db = Database()
        self.config = config

    def load_all_cogs(self):
        """Load all cogs from the Cogs directory, ignoring subdirectories."""
        print("\nLoading cogs...")
        loaded_count = 0
        total_cogs = 0

        cogs_dir = Path(__file__).parent / "Cogs"

        for item in cogs_dir.iterdir():
            # Skip directories (like 'old'), non-python files, and __pycache__
            if (
                item.is_dir()
                or not item.name.endswith(".py")
                or item.name.startswith("__")
            ):
                continue

            cog_path = f"Cogs.{item.stem}"
            total_cogs += 1

            try:
                self.load_extension(cog_path)
                print(f"\033[32m✓ Loaded {cog_path}\033[0m")
                loaded_count += 1
            except Exception as e:
                print(f"\033[31m✗ Failed to load {cog_path}: {e}\033[0m")

        print(f"\033[32m✓ Loaded {loaded_count}/{total_cogs} cogs\033[0m\n")


bot = HER(intents=disnake.Intents.all())


# Admin-only debug command for checking command status
@bot.slash_command(
    name="debugcmds",
    description="[ADMIN] Show command registration info",
)
async def debug_commands(inter: disnake.ApplicationCommandInteraction):
    """Show detailed info about registered commands"""
    # Check if user is admin
    admin_ids = config.get("admin_user_ids", [])
    if inter.author.id not in admin_ids:
        await inter.response.send_message(
            "You don't have permission to use this command.", ephemeral=True
        )
        return

    await inter.response.defer(ephemeral=True)

    # Get info about registered commands
    guild_commands = []
    global_commands = []

    for cmd in bot.application_commands:
        if hasattr(cmd, "guild_ids") and cmd.guild_ids:
            guild_commands.append(f"{cmd.name} (guilds: {cmd.guild_ids})")
        else:
            global_commands.append(cmd.name)

    msg = f"**Command Registration Info**\n\n"
    msg += f"**Total commands:** {len(bot.application_commands)}\n"
    msg += f"**Global commands:** {len(global_commands)}\n"
    msg += f"**Guild-specific:** {len(guild_commands)}\n"
    msg += f"**Dev mode:** {config.get('development_mode', False)}\n\n"

    if global_commands:
        msg += "**Global commands:**\n" + "\n".join(
            f"- {c}" for c in global_commands[:15]
        )

    if guild_commands:
        msg += "\n\n**Guild commands:**\n" + "\n".join(
            f"- {c}" for c in guild_commands[:10]
        )

    await inter.followup.send(msg, ephemeral=True)


# ==================== Event Handlers ====================


async def setup_hook():
    """
    A coroutine to be called to setup the bot, before it logs in.
    This is a good place for database connections and loading cogs.
    """
    try:
        print("Initializing services...\n")

        # Load cogs
        bot.load_all_cogs()

        # Connect to the database
        await bot.db.connect()

        # Ensure data directory exists
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)

        # Initialize log file
        log_file = data_dir / "bot_logs.json"
        if not log_file.exists():
            log_file.write_text("[]")

    except Exception as e:
        print(f"\033[31m✗ Failed during setup_hook: {e}\033[0m")
        await bot.close()  # Exit if setup fails


@bot.event
async def on_ready():
    """Initialize bot when ready. Runs only once per session."""
    startup_time = time.time() - bot.launch_time

    # Check database status now that it's connected
    db_status = "✅" if bot.db.pool else "❌"

    # Show command sync status
    print("\n" + "=" * 50)
    print("Command Sync Status:")
    print(f"Bot is in {len(bot.guilds)} guild(s):")
    for guild in bot.guilds:
        print(f"  - {guild.name} (ID: {guild.id})")

    print(f"\nTotal commands registered: {len(bot.application_commands)}")

    if config.get("development_mode", False):
        test_guild = config.get("testing_guild_id")
        print(f"✓ Development mode: Commands auto-sync to test guild {test_guild}")
        print("  → Commands appear INSTANTLY in test guilds")
    else:
        print("✓ Production mode: Commands are global")
        print("  → May take up to 1 hour to sync globally")
    print("=" * 50 + "\n")

    # Log startup info
    status_parts = [
        f"Connected as: {bot.user}",
        f"Startup time: {startup_time:.2f}s",
        f"Database: {db_status}",
        f"Active cogs: {len(bot.cogs)}",
        f"Commands registered: {len(bot.application_commands)}",
    ]
    status = "\n".join(status_parts)
    print(f"\033[32m=== Bot Ready ===\n{status}\n===============\033[0m\n")

    # Optional: List servers
    if bot.config.get("list_startup", False):
        await get_servers()


@bot.event
async def on_disconnect():
    """Called when bot temporarily disconnects."""
    print("\033[33m⚠ Bot temporarily disconnected...\033[0m")


# ==================== Utility Functions ====================


async def get_servers():
    """Display all servers the bot is in with invite links."""
    for guild in bot.guilds:
        print(f"\nServer: {guild.name} (ID: {guild.id})")

        try:
            invites = await guild.invites()
            if invites:
                if guild.id == 1382763556642099240:
                    # Special case: hide most invites for large server
                    print(f"Invite: {invites[0].url}")
                    if len(invites) > 1:
                        print(f"Invite: [{len(invites) - 1} more...]")
                else:
                    for invite in invites:
                        print(f"Invite: {invite.url}")
            else:
                # Create temporary invite if none exist
                if guild.me.guild_permissions.create_instant_invite:
                    invite = await guild.text_channels[0].create_invite(
                        max_age=3600, max_uses=1
                    )
                    print(f"Generated invite: {invite.url}")
                else:
                    print("No invites found and cannot create one.")
        except disnake.Forbidden:
            print("Bot does not have permission to view invites.")


async def shutdown():
    """Gracefully shut down the bot and close connections."""
    print("\n\033[33m=== Shutting down bot ===\033[0m")
    try:
        if bot.db and bot.db.pool:
            await bot.db.close()
            print("✓ Database connection closed")

        await bot.close()
        print("✓ Bot connection closed")
        print("\033[32m✓ Shutdown complete\033[0m\n")
    except Exception as e:
        print(f"\033[31m✗ Error during shutdown: {e}\033[0m")


# ==================== Main ====================


async def main():
    """Main entry point. Handles startup and error handling."""
    try:
        await setup_hook()
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n\033[33m⚠ Received keyboard interrupt\033[0m")
    except Exception as e:
        print(f"\033[31m✗ Bot crashed: {e}\033[0m")
        import traceback

        traceback.print_exc()
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[33m⚠ Forced shutdown\033[0m")
