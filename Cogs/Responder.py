import datetime
import os
import random
import re
import time
from datetime import datetime, timezone

import disnake
import yaml
from disnake.ext import commands

from Modules import log
from Modules.Database import Database

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Go one folder up and join with config.yml
config_path = os.path.join(current_dir, "..", "config.yml")

# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    data = yaml.safe_load(f)
    RESTRICTED = data.get("restricted_channels", [])
    COOLDOWN = int(data.get("cooldown", 60))


class MessageResponder(commands.Cog):
    GIF_URL_RE = re.compile(
        r"https?://cdn\.discordapp\.com/attachments/\d+/\d+/\S+\.gif", re.IGNORECASE
    )

    OLD_GIF_URL = (
        "https://cdn.discordapp.com/attachments/1382763557816500227/1400565040100409405/"
        "5NHcc2CSekZ0u3Cb8cVYKCbvDwGz3O372m9bteYZvljpiaUeyaodrWuuML0UK7iDMWilkUkQJR2Pl1xEaOC86BvHHf2RjbJfjWqOStrVYQnxzXEOkT6QzV9nFE7zTuh1TmUh3B74WN9naNsF4wU2tgLHJQ2DtlCcjCwoWrfdZuVMoUiRMp6ZqlWTK3TeHLUDeWlnXi6CuCmHK67geXDD0zh9B5iOiFWxl5fX6OQBPmLdhRpMpItCjnDuxCeCSlItsk9ZU9RALGfmLPFSTBDcE79OTrKanVNJZFHfF74QFrTq839ZYAeNGoEzBInEaC9dgtrlZ2bF640olzMbOx1XB6G9xmyp0ibkSarknXVGiEVPtgDatFrGbo14uZ1x5lZMXlqheNjbq1Bof3JsaL6PD1MpPsVhir6Cjuns4pJl8yWdBHdWKC1xtzLZSH3nKQXAxzNmy8ZFEKBvE2KowiTjgFid0tngNkt0zho1OZ9NJgk7eA8r7VjFQXiB9D1X..gif"
    )
    TARGET_GIF_URL = "https://tenor.com/view/them-ctf-scream-scream-if-you-love-them-the-rock-gif-5196550339096611233"

    def __init__(self, bot):
        self.bot = bot
        self.last_trigger_time = 0
        self.them_emoji = "<:them:1410349269948436530>"
        # Read config
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

    async def cog_load(self):
        """Called when the cog is loaded"""
        if self.config.get("read_dms_on_start", False):
            await self.fetch_missed_dms()

    async def fetch_missed_dms(self):
        """Fetch and save DMs that were received while bot was offline"""
        try:
            # Get timestamp of last logged DM
            last_dm = await Database.get_latest_dm_timestamp()

            for dm_channel in self.bot.private_channels:
                if isinstance(dm_channel, disnake.DMChannel):
                    # Fetch message history since last logged DM
                    async for message in dm_channel.history(
                        limit=None, after=last_dm, oldest_first=True
                    ):
                        if not message.author.bot:
                            await Database.log_dm(
                                user_id=message.author.id,
                                username=str(message.author),
                                content=message.content,
                                message_id=message.id,
                                has_attachments=bool(message.attachments),
                                attachment_count=len(message.attachments),
                            )
            print("Successfully caught up on missed DMs")
        except Exception as e:
            print(f"Error fetching missed DMs: {e}")

    async def handle_them_message(self, message: disnake.Message):
        # Check if message is a reply and contains "good"
        if (
            message.reference
            and "good" in message.content.lower()
            and not message.author.bot
        ):
            try:
                # Get the message being replied to
                replied_msg = await message.channel.fetch_message(
                    message.reference.message_id
                )
                # Check if the replied message is from our bot
                if replied_msg.author.id == self.bot.user.id:
                    await message.add_reaction("❤️")
            except (disnake.NotFound, disnake.Forbidden):
                pass

        # Return if message is from a bot or in restricted channel or DM
        if (
            message.author.bot
            or message.channel.id in RESTRICTED
            or isinstance(message.channel, disnake.DMChannel)
        ):
            return

        content = message.content or ""

        # Check if message contains "them" keyword (case insensitive)
        has_keyword = any(
            keyword in content.lower() for keyword in ["them", self.them_emoji]
        )

        # Check for exact target GIF URL
        has_exact_gif_url = (
            self.TARGET_GIF_URL in content
            or any(
                embed.image
                and isinstance(embed.image.url, str)
                and embed.image.url == self.TARGET_GIF_URL
                for embed in message.embeds
            )
            or any(att.url == self.TARGET_GIF_URL for att in message.attachments)
        )

        # Check cooldown
        time_since = time.time() - self.last_trigger_time
        if time_since < COOLDOWN:
            return

        if any([has_keyword, has_exact_gif_url]):
            import random

            reaction_choice = random.randint(0, 4)
            match reaction_choice:
                case 0:
                    await message.channel.send(f"{self.them_emoji} :on: :top:")
                case 1:
                    await message.channel.send("THEM?! ON?! TOP?!")
                case 2:
                    await message.channel.send("THEM ON TOP")
                case 3:
                    await message.channel.send(self.TARGET_GIF_URL)
                case 4:
                    await message.add_reaction(self.them_emoji)
                    await message.add_reaction("⬆️")
                    await message.add_reaction("🔝")

            # Increment the counter
            await Database.increment_them_counter()
            print(
                f"\033[34m{message.author.display_name} triggered THEM response\033[0m"
            )
            self.last_trigger_time = time.time()

    async def handle_dm(self, message):
        """Handle DM messages"""
        user = message.author
        content = message.content

        print(f"DM from {user.name}: {content}")

        # Log DM
        await Database.log_dm(
            user_id=user.id,
            username=str(user),
            content=content,
            message_id=message.id,
            has_attachments=bool(message.attachments),
            attachment_count=len(message.attachments),
        )

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        # Handle DMs
        if isinstance(message.channel, disnake.DMChannel):
            if not message.author.bot:
                await self.handle_dm(message)
            return

        # Handle server messages
        await self.handle_them_message(message)

    class DM_Manager:
        def __init__(self, bot):
            self.bot = bot
            self.reply = False

        @commands.Cog.listener()
        async def on_message(self, message):
            """Handle all messages, including DMs"""
            # Ignore messages from bots (including this bot)
            if message.author.bot:
                return

            # Check if message is a DM (no guild)
            if message.guild is None:
                await self.handle_dm(message)

        async def handle_dm(self, message):
            """Handle DM messages"""
            user = message.author
            content = message.content

            print(f"DM from {user.name}#{user.discriminator}: {content}")

            # Log to file (optional)
            self.log_dm_to_file(user, content, message)

            # Auto-reply to DMs
            if self.reply != False:
                if content.lower().startswith("hello"):
                    await message.reply(
                        "Hello! I received your DM. How can I help you?"
                    )
                elif content.lower().startswith("help"):
                    await message.reply(
                        "Here are the commands you can use:\n• `hello` - Say hello\n• `info` - Get your user info\n• `link` - Link your account via OAuth2"
                    )
                elif content.lower().startswith("info"):
                    embed = disnake.Embed(
                        title="Your Information", color=disnake.Color.blue()
                    )
                    embed.add_field(
                        name="Username", value=f"{user.name}#{user.discriminator}"
                    )
                    embed.add_field(name="User ID", value=user.id)
                    embed.add_field(
                        name="Account Created",
                        value=user.created_at.strftime("%Y-%m-%d"),
                    )
                    if user.avatar:
                        embed.set_thumbnail(url=user.avatar.url)
                    await message.reply(embed=embed)

        async def log_dm(self, user, content, message):
            """Log DM to database"""
            try:
                await Database.log_dm(
                    user_id=user.id,
                    username=str(user),
                    content=content,
                    message_id=message.id,
                    has_attachments=bool(message.attachments),
                    attachment_count=len(message.attachments),
                )
            except Exception as e:
                print(f"Failed to log DM to database: {e}")

        # Command to send DM to a user (admin only)
        @commands.slash_command(name="starry", description="ALSO TESTING")
        async def send_dm(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.User,
            *,
            example: str,
        ):
            """Send a DM to a specific user"""
            try:
                await user.send(example)
                await inter.response.send_message(
                    f"✅ DM sent to {user.mention}", ephemeral=True
                )
            except disnake.Forbidden:
                await inter.response.send_message(
                    f"❌ Cannot send DM to {user.mention} (they have DMs disabled or blocked the bot)",
                    ephemeral=True,
                )
            except Exception as e:
                await inter.response.send_message(
                    f"❌ Failed to send DM: {str(e)}", ephemeral=True
                )

        # Command to get recent DM logs (admin only)
        @log(text="DM logs command was used", color=0x00FF00)
        @commands.slash_command(
            name="dm_logs",
            description="View recent DM logs",
            default_member_permissions=disnake.Permissions(administrator=True),
        )
        async def dm_logs(
            self,
            inter: disnake.ApplicationCommandInteraction,
            limit: int = commands.Param(
                description="Number of logs to show", default=10
            ),
        ):
            """View recent DM logs"""
            if inter.author.id != 733839959009525761:  # Keep the owner check
                await inter.response.send_message("no", ephemeral=True)
                return

            await inter.response.defer(ephemeral=True)

            try:
                logs = await Database.get_recent_dms(limit)

                if not logs:
                    await inter.followup.send("❌ No DM logs found", ephemeral=True)
                    return

                embed = disnake.Embed(
                    title=f"📬 Recent DM Logs ({len(logs)} messages)",
                    color=disnake.Color.blue(),
                )

                log_text = []
                for log in logs:
                    time_str = log["timestamp"].strftime("%m/%d %H:%M")
                    content_preview = log["content"][:50] + (
                        "..." if len(log["content"]) > 50 else ""
                    )
                    attachments = " 📎" if log["has_attachments"] else ""

                    log_text.append(
                        f"`{time_str}` **{log['username']}**:{attachments} {content_preview}"
                    )

                embed.description = "\n".join(log_text)
                await inter.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await inter.followup.send(
                    f"❌ Error reading logs: {str(e)}", ephemeral=True
                )

    class Server_Manager:
        @commands.Cog.listener()
        async def on_message(self, message: disnake.Message):
            # Check if message is a reply and contains "good"
            if (
                message.reference
                and "good" in message.content.lower()
                and not message.author.bot
            ):
                try:
                    # Get the message being replied to
                    replied_msg = await message.channel.fetch_message(
                        message.reference.message_id
                    )
                    # Check if the replied message is from our bot
                    if replied_msg.author.id == self.bot.user.id:
                        await message.add_reaction("❤️")
                except (disnake.NotFound, disnake.Forbidden):
                    pass

        @commands.Cog.listener()
        async def on_message(self, message: disnake.Message):
            if (
                message.author.bot
                or message.channel.id in RESTRICTED
                or isinstance(message.channel, disnake.DMChannel)
            ):
                return

            content = message.content or ""

            # Check if message contains "them" keyword (case insensitive)
            has_keyword = any(
                keyword in content.lower() for keyword in ["them", self.them_emoji]
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
            has_gif_embed = all(
                embed.image
                and isinstance(embed.image.url, str)
                and embed.image.url.lower().endswith(".gif")
                for embed in message.embeds
            )

            # Final condition: trigger if keyword or exact GIF URL or any other gif present
            time_since = time.time() - self.last_trigger_time

            if time_since < COOLDOWN:
                return
            if any(
                [
                    has_keyword,
                    has_exact_gif_url,
                    # has_gif_attachment,
                    # has_gif_url,
                    # has_gif_embed
                ]
            ):
                reaction_choice = random.randint(0, 4)
                match reaction_choice:
                    case 0:
                        await message.channel.send(f"{self.them_emoji} :on: :top:")
                    case 1:
                        await message.channel.send("THEM?! ON?! TOP?!")
                    case 2:
                        await message.channel.send("THEM ON TOP")
                    case 3:
                        await message.channel.send(self.TARGET_GIF_URL)
                    case 4:
                        await message.add_reaction(self.them_emoji)
                        await message.add_reaction(":on:")
                        await message.add_reaction(":top:")

                print(
                    f"\033[34m{message.author.display_name} triggered THEM response\033[0m"
                )
                self.last_trigger_time = time.time()
                # themCounter += 1 # TODO: make this work using postgres

            # time.sleep(5)  # commented out to avoid blocking async loop


def setup(bot):
    bot.add_cog(MessageResponder(bot))
    # bot.add_cog(MessageResponder.DM_Manager(bot))
