import datetime
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
    COOLDOWN = int(data.get("COOLDOWN", []))


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
        self.last_trigger_time = 0
        self.them_emoji = str("<:them:1410349269948436530>")

    class DM_Manager:
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
            if content.lower().startswith("hello"):
                await message.reply("Hello! I received your DM. How can I help you?")
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
                    name="Account Created", value=user.created_at.strftime("%Y-%m-%d")
                )
                if user.avatar:
                    embed.set_thumbnail(url=user.avatar.url)
                await message.reply(embed=embed)
            else:
                # Generic response for other messages
                await message.reply(
                    f"I received your message: \"{content}\"\n\nType 'help' for available commands!"
                )

        def log_dm_to_file(self, user, content, message):
            """Log DM to a JSON file"""
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "user_id": user.id,
                "username": f"{user.name}#{user.discriminator}",
                "content": content,
                "message_id": message.id,
                "has_attachments": len(message.attachments) > 0,
                "attachment_count": len(message.attachments),
            }
            print(log_entry)
            # Append to log file
            try:
                with open("dm_logs.json", "a", encoding="utf-8") as f:
                    f.write(json5.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"Failed to log DM: {e}")

        # Command to send DM to a user (admin only)
        @commands.slash_command(description="[Admin] Send a DM to a user")
        @commands.has_role("Moderator")
        async def send_dm(
            self,
            inter: disnake.ApplicationCommandInteraction,
            user: disnake.User,
            *,
            message: str,
        ):
            """Send a DM to a specific user"""
            try:
                await user.send(message)
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
        @commands.slash_command(description="[Admin] View recent DM logs")
        @commands.has_role("Moderator")
        async def dm_logs(
            self, inter: disnake.ApplicationCommandInteraction, limit: int = 10
        ):
            """View recent DM logs"""
            try:
                with open("dm_logs.json", "r", encoding="utf-8") as f:
                    lines = f.readlines()

                if not lines:
                    await inter.response.send_message(
                        "❌ No DM logs found", ephemeral=True
                    )
                    return

                # Get the last N lines
                recent_logs = lines[-limit:]

                embed = disnake.Embed(
                    title=f"📬 Recent DM Logs ({len(recent_logs)} messages)",
                    color=disnake.Color.blue(),
                )

                log_text = []
                for line in recent_logs:
                    try:
                        log_entry = json5.loads(line.strip())
                        timestamp = datetime.datetime.fromisoformat(
                            log_entry["timestamp"]
                        )
                        time_str = timestamp.strftime("%m/%d %H:%M")
                        content_preview = log_entry["content"][:50] + (
                            "..." if len(log_entry["content"]) > 50 else ""
                        )

                        log_text.append(
                            f"`{time_str}` **{log_entry['username']}**: {content_preview}"
                        )
                    except:
                        continue

                embed.description = (
                    "\n".join(log_text) if log_text else "No valid logs found"
                )
                await inter.response.send_message(embed=embed, ephemeral=True)

            except FileNotFoundError:
                await inter.response.send_message(
                    "❌ No DM log file found", ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(
                    f"❌ Error reading logs: {str(e)}", ephemeral=True
                )

    class Server_Manager:
        @commands.Cog.listener()
        async def on_message(self, message: disnake.Message):
            return

        # if replying to bot with good bot then heart the message

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
                # themCounter += 1 # TODO: make this use a json5 file (cuz fk you i like json5 more then json) -starry

            # time.sleep(5)  # commented out to avoid blocking async loop


def setup(bot):
    bot.add_cog(MessageResponder(bot))
