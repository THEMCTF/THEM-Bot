import asyncio
import os
import sys
import time

import disnake
import yaml
from disnake.ext import commands
from dotenv import load_dotenv

from Modules.Logger import Logger, setup_logger

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
    ]

    async def load_cog(cog):
        try:
            bot.load_extension(cog)
            print(f"\033[32mLoaded {cog}\033[0m")
            return True
        except Exception as e:
            print(f"\033[31mFailed to load extension {cog}: {e}\033[0m")
            return False

    print("Loading cogs...")
    # Load all cogs concurrently with progress tracking
    results = await asyncio.gather(*[load_cog(cog) for cog in cogs])
    loaded = sum(1 for r in results if r)
    print(f"\033[32mSuccessfully loaded {loaded}/{len(cogs)} cogs\033[0m")


# Initialize bot startup
async def init_bot():
    print("Starting bot initialization...")

    # Initialize database first
    print("Initializing database...")
    try:
        # Set up logger right after bot is created
        print("Initializing logger...")
        await setup_logger(bot)
        print("\033[32mLogger initialized successfully\033[0m")
        await Database.init()
        if not Database.conn:
            raise Exception("Database connection not established")
        print("\033[32mDatabase initialized successfully\033[0m")
    except Exception as e:
        print(f"\033[31mFailed to initialize database: {e}\033[0m")
        sys.exit(1)

    # Then load cogs
    await load_cogs()


# Load cogs and initialize bot
loop = asyncio.get_event_loop()
loop.run_until_complete(init_bot())


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

    # Initialize database, logger, and any other async startup tasks concurrently
    try:
        print("Initializing services...")

        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)

        # Update status based on initialization results
        status_parts = [
            f"Connected as: {bot.user}",
            f"Startup time: {startup_time:.2f}s",
            f"Database: {'✅' if Database.conn else '❌'}",
            f"Active cogs: {len(bot.cogs)}",
            f"Data directory: {'✅' if os.path.exists(data_dir) else '❌'}",
        ]
        status = "\n".join(status_parts)

        # Log to console with color
        print(f"\033[32m=== Bot Ready ===\n{status}\n===============\033[0m")

        # Log to Discord if enabled and logger is available
        if list_startup:
            await Logger().log(
                text=f"🚀 Bot is online! Startup took {startup_time:.2f}s",
                color=0x00FF00,
                type="Startup",
                priority=1,
                user=bot.user,
            )

        # Initialize log files
        if not os.path.exists(os.path.join(data_dir, "bot_logs.json")):
            with open(os.path.join(data_dir, "bot_logs.json"), "w") as f:
                f.write("[]")

    except Exception as e:
        print(f"\033[31mFailed to initialize services: {e}\033[0m")


# Run the bot and monitor the file concurrently
bot.run(TOKEN)
