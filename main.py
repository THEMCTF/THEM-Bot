import asyncio
import os
import sys
import time

import disnake
import yaml
from disnake.ext import commands
from dotenv import load_dotenv

from Modules.Logger import setup_logger

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
    data = yaml.safe_load(f)
    GUILD_ID = data.get("guild_id")
    list_startup = data.get("list_startup", False)


from Modules.Database import Database

# Create the bot without a command prefix since we're using ONLY slash commands.
bot = commands.InteractionBot(intents=disnake.Intents.all())
bot.launch_time = time.time()  # Track when the bot started


# Load cogs in parallel for faster startup
async def load_cogs():
    cogs = [
        "Cogs.General",  # General commands
        "Cogs.Responder",  # Responder
        "Cogs.Moderation",
        "Cogs.CTFtime",
        "Cogs.CTFother",
        "Cogs.ChangelogMonitor",  # Changelog monitoring and notifications
    ]

    async def load_cog(cog):
        try:
            bot.load_extension(cog)
        except Exception as e:
            print(f"Failed to load extension {cog}: {e}")

    # Load all cogs concurrently
    await asyncio.gather(*[load_cog(cog) for cog in cogs])


# Load cogs
loop = asyncio.get_event_loop()
loop.run_until_complete(load_cogs())


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
    # Start timing after connection is established
    startup_time = time.time() - bot.launch_time

    # Initialize database and logger concurrently
    try:
        db_init, logger = await asyncio.gather(Database.init(), setup_logger(bot))
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        logger = None

    # Build status message
    status_parts = [
        f"Loaded cogs: {', '.join(bot.cogs.keys())}",
        f"Startup time: {startup_time:.2f}s",
        f"Connected as: {bot.user}",
        "Database: ✅" if Database.conn else "Database: ❌",
    ]
    status = "\n".join(status_parts)

    # Log to console with color
    print(f"\033[32m{status}\033[0m")

    # Log to Discord if enabled and logger is available
    if list_startup and logger:
        try:
            await logger.log(
                text=f"Bot is online! Startup took {startup_time:.2f}s",
                color=0x00FF00,
                type="Startup",
                priority=1,
                user=bot.user,
            )
        except Exception as e:
            print(f"Failed to send startup log: {e}")


# Run the bot and monitor the file concurrently
bot.run(TOKEN)
