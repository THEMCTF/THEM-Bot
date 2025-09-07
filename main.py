import asyncio
import os

import disnake
import json5
from disnake.ext import commands
from dotenv import load_dotenv

photo = """\033[32m hi\033[0m"""

print(photo)
load_dotenv()

# Token is hidden
TOKEN = os.getenv("TOKEN")
GUILD_ID = int(os.getenv("SERVER"))


# Create the bot without a command prefix since we're using ONLY slash commands.
bot = commands.InteractionBot(intents=disnake.Intents.all())

# Load cogs (ensure these .py files exist in your bot's folder).
bot.load_extension("Cogs.General")  # General commands
bot.load_extension("Cogs.Responder")  # Responder duh
bot.load_extension("Cogs.Moderation")
# bot.load_extension("Cogs.Starry")
bot.load_extension("Cogs.Outside")
bot.load_extension("Cogs.CTFtime")
bot.load_extension("Cogs.CTFother")


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


# Run the bot and monitor the file concurrently
bot.run(TOKEN)
