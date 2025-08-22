import os
import random
import re
import time

import disnake
import json5
from disnake.ext import commands

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Go one folder up and join with config.json5
config_path = os.path.join(current_dir, "..", "config.json5")

# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    data = json5.load(f)
    RESTRICTED = data.get("RESTRICTED", [])


class MessageResponder(commands.Cog):
    GIF_URL_RE = re.compile(
        r"https?://cdn\.discordapp\.com/attachments/\d+/\d+/\S+\.gif", re.IGNORECASE
    )

    TARGET_GIF_URL = (
        "https://cdn.discordapp.com/attachments/1382763557816500227/1400565040100409405/"
        "5NHcc2CSekZ0u3Cb8cVYKCbvDwGz3O372m9bteYZvljpiaUeyaodrWuuML0UK7iDMWilkUkQJR2Pl1xEaOC86BvHHf2RjbJfjWqOStrVYQnxzXEOkT6QzV9nFE7zTuh1TmUh3B74WN9naNsF4wU2tgLHJQ2DtlCcjCwoWrfdZuVMoUiRMp6ZqlWTK3TeHLUDeWlnXi6CuCmHK67geXDD0zh9B5iOiFWxl5fX6OQBPmLdhRpMpItCjnDuxCeCSlItsk9ZU9RALGfmLPFSTBDcE79OTrKanVNJZFHfF74QFrTq839ZYAeNGoEzBInEaC9dgtrlZ2bF640olzMbOx1XB6G9xmyp0ibkSarknXVGiEVPtgDatFrGbo14uZ1x5lZMXlqheNjbq1Bof3JsaL6PD1MpPsVhir6Cjuns4pJl8yWdBHdWKC1xtzLZSH3nKQXAxzNmy8ZFEKBvE2KowiTjgFid0tngNkt0zho1OZ9NJgk7eA8r7VjFQXiB9D1X..gif"
    )

    def __init__(self, bot):
        self.bot = bot

    @bot.event
    async def on_reaction_add(reaction, user):
        if user == bot.user:  # Ignore reactions from the bot itself
            return

        print(f"{user.display_name} reacted with {reaction.emoji} on message ID {reaction.message.id}")

        # Example: Check for a specific emoji
        if str(reaction.emoji) == "👍":
            await reaction.message.channel.send(f"Someone liked it!")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or message.channel.id in RESTRICTED:
            return

        content = message.content or ""

        # Check if message contains "them" keyword (case insensitive)
        has_keyword = any(
            keyword in content.lower()
            for keyword in ["them", "<:them:1400018402059485224> :on: :top:"]
        )

        # Check if exact target GIF URL is anywhere
        has_exact_gif_url = (
            self.TARGET_GIF_URL in content
            or any(
                embed.image
                and isinstance(embed.image.url, str)
                and embed.image.url == self.TARGET_GIF_URL
                for embed in message.embeds
            )
            or any(
                att.url == self.TARGET_GIF_URL
                or att.filename == self.TARGET_GIF_URL.split("/")[-1]
                for att in message.attachments
            )
        )

        # Also check if any other .gif attachments or URLs exist
        has_gif_attachment = any(
            att.filename.lower().endswith(".gif") for att in message.attachments
        )
        has_gif_url = bool(self.GIF_URL_RE.search(content))
        has_gif_embed = any(
            embed.image
            and isinstance(embed.image.url, str)
            and embed.image.url.lower().endswith(".gif")
            for embed in message.embeds
        )

        # Final condition: trigger if keyword or exact GIF URL or any other gif present
        if (
            has_keyword
            or has_exact_gif_url
            or has_gif_attachment
            or has_gif_url
            or has_gif_embed
        ):
            await them_reaction(message=message)

    async def them_reaction(self, message: disnake.Message):
        reaction_choice = random.randint(0, 3)
        match reaction_choice:
            case 0:
                await message.channel.send("<:THEM:1400018402059485224> :on: :top:")
            case 1:
                await message.channel.send("THEM?! ON?! TOP?!")
            case 2:
                await message.channel.send("THEM ON TOP")
            case 3:
                await message.channel.send(self.TARGET_GIF_URL)

        print(
            f"\033[34m{message.author.display_name} triggered THEM response\033[0m"
        )# TODO: use logging
        themCounter += 1 # TODO: make this use a json5 file (cuz fk you i like json5 more then json) -starry


def setup(bot):
    bot.add_cog(MessageResponder(bot))
