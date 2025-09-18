import os

import disnake
import json5
from disnake.ext import commands
from dotenv import load_dotenv

from Modules import setup_logger

photo = """\033[32m hi\033[0m"""

print(photo)
load_dotenv()

# Token is hidden
TOKEN = os.getenv("TOKEN")
# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Join with config.json5
config_path = os.path.join(current_dir, "config.json5")

# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    data = json5.load(f)
    GUILD_ID = data.get("GUILD_ID", [])


# Create the bot without a command prefix since we're using ONLY slash commands.
bot = commands.InteractionBot(intents=disnake.Intents.all())

setup_logger(bot)

# Load cogs (ensure these .py files exist in your bot's folder).
bot.load_extension("Cogs.General")  # General commands
bot.load_extension("Cogs.Responder")  # Responder duh
bot.load_extension("Cogs.Moderation")
bot.load_extension("Cogs.Outside")
bot.load_extension("Cogs.CTFtime")
bot.load_extension("Cogs.CTFother")


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
async def on_ready():  # TODO: FIX
    # List all application commands
    # help_text = f"\033[34mAvailable slash commands:\n"
    # for cmd in bot.application_commands:
    #     help_text += f"/{cmd.name}: {cmd.description}\n"
    # print(help_text)

    # List all loaded cogs
    print("\033[32mCogs loaded:", list(bot.cogs.keys()))

    print(f"\033[32mBot is ready and logged in as {bot.user}\033[0m")
    # await get_servers()


# Run the bot and monitor the file concurrently
bot.run(TOKEN)
