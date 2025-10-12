import asyncio
import os
import sys
import time

import disnake
import yaml
from disnake.ext import commands
from dotenv import load_dotenv

from Modules.Database import Database
from Modules.Logger import Logger

photo = """\033[32m hi\033[0m"""

print(photo)
load_dotenv()

# Token is hidden
TOKEN = os.getenv("TOKEN")
# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Join with config.yml
config_path = os.path.join(current_dir, "config.yml")

# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    config = yaml.safe_load(f)


class HER(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.launch_time = time.time()
        self.db = Database()
        self.config = config

    # Cogs will be loaded in on_ready to ensure bot is fully connected.
    async def load_all_cogs(self):
        """Loads all cogs in parallel."""
        cogs_to_load = [
            "Cogs.General",
            "Cogs.Tickets",
            "Cogs.Moderation",
            # "Cogs.Responder",
            # "Cogs.CTFtime",
            # "Cogs.CTFother",
        ]

        print("\nLoading cogs...")
        loaded_count = 0
        for cog in cogs_to_load:
            try:
                self.load_extension(cog)
                print(f"\033[32mLoaded {cog}\033[0m")
                loaded_count += 1
            except Exception as e:
                print(f"\033[31mFailed to load extension {cog}: {e}\033[0m")
            else:
                pass  # Already printed success

        print(
            f"\033[32mSuccessfully loaded {loaded_count}/{len(cogs_to_load)} cogs\033[0m"
        )


bot = HER(intents=disnake.Intents.all())


async def get_servers():
    for guild in bot.guilds:
        print(f"\nServer: {guild.name} (ID: {guild.id})")

        # Try to fetch existing invites
        try:
            invites = await guild.invites()
            if invites:
                if guild.id == 1382763556642099240:
                    # Build a display-only list
                    invites_display = [invites[0].url, f"[{len(invites) - 1} more...]"]
                else:
                    # Normal case: show all invite URLs
                    invites_display = [invite.url for invite in invites]

                for invite_str in invites_display:
                    print(f"Invite: {invite_str}")
            else:
                # Create a temporary invite if none exist
                if guild.me.guild_permissions.create_instant_invite:
                    invite = await guild.text_channels[0].create_invite(
                        max_age=3600, max_uses=1
                    )
                    print(f"Generated invite: {invite.url}")
                else:
                    print("No invites found and cannot create one.")
        except disnake.Forbidden:
            print("Bot does not have permission to view invites.")


@bot.event
async def on_ready():
    # Prevent setup from running more than once
    if not bot.is_ready() or bot.is_closed():
        return
    # Start timing after connection is established
    startup_time = time.time() - bot.launch_time

    # Initialize database and other async startup tasks
    try:
        print("Initializing services...")

        # Load cogs now that the bot is fully ready
        await bot.load_all_cogs()

        # Connect to database
        await bot.db.connect()
        db_status = "✅" if bot.db.pool else "❌"

        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)

        # Update status based on initialization results
        status_parts = [
            f"Connected as: {bot.user}",
            f"Startup time: {startup_time:.2f}s",
            f"Database: {db_status}",
            f"Active cogs: {len(bot.cogs)}",
            f"Data directory: {'✅' if os.path.exists(data_dir) else '❌'}",
        ]
        status = "\n".join(status_parts)

        # Log to console with color
        print(f"\033[32m=== Bot Ready ===\n{status}\n===============\033[0m")

        # Initialize log files
        if not os.path.exists(os.path.join(data_dir, "bot_logs.json")):
            with open(os.path.join(data_dir, "bot_logs.json"), "w") as f:
                f.write("[]")

        # Optional: List servers if configured
        if bot.config.get("list_startup", False):
            await get_servers()

    except Exception as e:
        print(f"\033[31mFailed to initialize services: {e}\033[0m")


@bot.event
async def on_disconnect():
    """Clean up when bot disconnects (temporary disconnects)"""
    print("Bot temporarily disconnected...")
    # Don't close database on temporary disconnects - it will reconnect


async def shutdown():
    """Graceful shutdown procedure"""
    print("\n\033[33m=== Shutting down bot ===\033[0m")
    try:
        # Close database connection
        if bot.db and bot.db.pool:
            await bot.db.close()
            print("✓ Database connection closed")

        # Close bot connection
        await bot.close()
        print("✓ Bot connection closed")

        print("\033[32m✓ Shutdown complete\033[0m")
    except Exception as e:
        print(f"\033[31mError during shutdown: {e}\033[0m")


# Run the bot with proper error handling
async def main():
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n\033[33mReceived keyboard interrupt...\033[0m")
    except Exception as e:
        print(f"\033[31m\nBot crashed: {e}\033[0m")
        import traceback

        traceback.print_exc()
    finally:
        # Always clean up, regardless of how we exit
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[33mForced shutdown\033[0m")
