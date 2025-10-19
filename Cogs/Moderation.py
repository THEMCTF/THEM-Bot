import asyncio
import json
import os
import random
from datetime import datetime, timedelta, timezone

import aiohttp
import disnake
import dotenv
from disnake.ext import commands

import Modules.Website as Website
from Modules.Logger import logger

# use dotenv to get the api key for tenor
dotenv.load_dotenv()
TENOR_API_KEY = os.getenv("TENOR_API_KEY")


class ModerationCog(commands.Cog):
    def __init__(self, bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config

        # Configure the logger
        logger.configure(bot, config)

        # Load constants from config
        self.colors = self.config.get("colors", {})
        self.LOCKED_EMOJI = self.config.get("locked_emoji", "🔒")
        self.UNLOCKED_EMOJI = self.config.get("unlocked_emoji", "🔓")
        self.COLOR_RED = self.colors.get("red", 0xDD2E44)
        self.MODERATOR_ROLE_IDS = set(self.config.get("moderator_roles", []))
        self.banned_term = self.config.get("banned_gif_term", "banned")
        self.admin_user_ids = config.get("admin_user_ids", [])

        self._last_purge_timestamp: float = 0

    async def _purge_(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User = None,
        **kwargs,
    ):
        # if user id then only delete from that
        if user:
            deleted = await inter.channel.purge(
                **kwargs, check=lambda m: m.author.id == user.id
            )
        else:
            deleted = await inter.channel.purge(**kwargs)

        await inter.channel.send(self.config.get("purged_emoji"))

        msg = f"-# Deleted {len(deleted)} message"
        if len(deleted) > 1:
            msg += "s"
        if user:
            msg += f" from {str(user)}."
        await inter.followup.send(msg)

    @commands.slash_command(
        name="purge",
        description="Mass delete messages",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @commands.guild_only()
    @logger
    async def purge(
        self,
        inter: disnake.ApplicationCommandInteraction,
        amount: int = commands.Param(description="Number of messages to delete"),
        user: disnake.User = commands.Param(
            default=None, description="Only delete messages from this user"
        ),
        messageid: int = commands.Param(
            default=None, description="Only delete messages after this message"
        ),
    ):
        await inter.response.defer(ephemeral=True)

        if amount < 1 or amount > 100:
            await inter.followup.send(
                "Please specify a number between 1 and 100", ephemeral=True
            )
            return

        if messageid:
            await self._purge_(
                inter,
                user=user,
                limit=amount,
                after=messageid.created_at - timedelta(microseconds=1),
            )
        else:
            await self._purge_(
                inter,
                user=user,
                limit=amount,
            )

    @commands.message_command(
        name="purge",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.guild_only()
    @logger
    async def purge_from_message(
        self,
        inter: disnake.ApplicationCommandInteraction,
        message: disnake.Message,
    ):
        await inter.response.defer(ephemeral=True)
        await self._purge_(
            inter,
            limit=None,
            after=message.created_at - timedelta(microseconds=1),
            oldest_first=False,
        )

    @commands.slash_command(
        name="timeout",
        description="Time a user out",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @logger
    async def timeout(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="User to timeout"),
        duration: int = commands.Param(description="Duration in minutes"),
        reason: str = commands.Param(description="Reason for timeout"),
    ):
        # Check if user can be timed out
        if not isinstance(user, disnake.Member):
            await inter.response.send_message(
                "This command only works on server members", ephemeral=True
            )
            return

        if user.top_role >= inter.author.top_role:
            await inter.response.send_message(
                "You cannot timeout someone with a higher or equal role", ephemeral=True
            )
            return

        try:
            await user.timeout(duration=timedelta(minutes=duration), reason=reason)
            await inter.response.send_message(
                f"{user.mention} has been timed out for {duration}m\nReason: {reason}"
            )

        except disnake.Forbidden:
            await inter.response.send_message(
                "I don't have permission to timeout this user", ephemeral=True
            )
        except disnake.HTTPException as e:
            await inter.response.send_message(
                f"Failed to timeout user: {e}", ephemeral=True
            )

    @commands.slash_command(
        name="ban",
        description="Ban a user",
        default_member_permissions=disnake.Permissions(ban_members=True),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @logger
    async def ban(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member = commands.Param(description="User to ban"),
        reason: str = commands.Param(description="Reason for ban"),
    ):
        # can we ban this user?
        if not isinstance(user, disnake.Member):
            await inter.response.send_message(
                "This command only works on server members", ephemeral=True
            )
            return

        if user.top_role >= inter.author.top_role:
            await inter.response.send_message(
                "You cannot ban someone with a higher or equal role", ephemeral=True
            )
            return

        try:
            await inter.response.defer(ephemeral=True)

            gif_url = None
            if self.banned_term and TENOR_API_KEY:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://tenor.googleapis.com/v2/search",
                        params={
                            "q": self.banned_term,
                            "key": TENOR_API_KEY,
                            "limit": 50,
                            "media_filter": "gif",
                        },
                    ) as r:
                        if r.status == 200:
                            data = await r.json()
                            if data.get("results"):
                                gif_url = random.choice(
                                    data["results"]["media_formats"]["gif"]["url"]
                                )
                        else:
                            print(
                                f"Tenor API request failed with status {r.status}: {await r.text()}"
                            )

            if gif_url:
                await inter.channel.send(gif_url)
                await asyncio.sleep(10)

            await user.ban(reason=reason)

            await inter.channel.send(
                content=f"-# {user.mention} has been banned. Reason: {reason}"
            )

        except disnake.Forbidden:
            await inter.followup.send(
                "I don't have permission to ban this user", ephemeral=True
            )
        except disnake.HTTPException as e:
            await inter.followup.send(f"Failed to ban user: {e}", ephemeral=True)

    @commands.slash_command(
        name="lock",
        description="Lock the channel",
        default_member_permissions=disnake.Permissions(manage_channels=True),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @logger
    async def lock(
        self,
        inter: disnake.ApplicationCommandInteraction,
        reason: str = commands.Param(description="Reason"),
    ):
        await inter.response.defer()

        # Ensure the locked_channels table exists with the correct schema
        await self.db.create_table(
            "locked_channels",
            [
                ("channel_id", "BIGINT"),
                ("overwrites", "TEXT"),
                ("reason", "TEXT"),
            ],
        )

        # Check if channel is already locked in the DB
        existing = await self.db.find_rows(
            table_name="locked_channels",
            column_name="channel_id",
            value=inter.channel.id,
        )
        if existing:
            await inter.followup.send("This channel is already locked.")
            return

        serializable_overwrites = {
            str(target.id): tuple(p.value for p in overwrite.pair())
            for target, overwrite in inter.channel.overwrites.items()
        }
        overwrites_json = json.dumps(serializable_overwrites)

        await self.db.add_to_table(
            "locked_channels",
            [inter.channel.id, overwrites_json, reason],
            start_row="next",
            direction="row",  # start_col=1 is the default
        )

        # make it so @everyone can't send messages
        everyone_overwrite = inter.channel.overwrites_for(inter.guild.default_role)
        everyone_overwrite.send_messages = False
        await inter.channel.set_permissions(
            inter.guild.default_role, overwrite=everyone_overwrite
        )

        # make it so only @moderators and @admins can send messages
        for target, overwrite in inter.channel.overwrites.items():
            if (
                isinstance(target, disnake.Role)
                and target.id not in self.MODERATOR_ROLE_IDS
            ):
                overwrite.send_messages = False
                await inter.channel.set_permissions(target, overwrite=overwrite)

        embed = disnake.Embed(
            title=f"{self.LOCKED_EMOJI} Channel Locked",
            description=disnake.utils.escape_markdown(str(reason)),
            color=self.COLOR_RED,
        )
        embed.set_author(
            name=str(inter.author),
            icon_url=str(inter.author.avatar.url),
        )

        await inter.channel.send(embed=embed)

    @commands.slash_command(
        name="unlock",
        description="Unlock the channel",
        default_member_permissions=disnake.Permissions(manage_channels=True),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @logger
    async def unlock(
        self,
        inter: disnake.ApplicationCommandInteraction,
    ):
        await inter.response.defer()
        # Find the lock data in the database
        lock_rows = await self.db.find_rows(
            "locked_channels", "channel_id", inter.channel.id
        )

        if not lock_rows:
            await inter.followup.send(
                "This channel was not locked by me or has already been unlocked.",
                ephemeral=True,
            )
            return

        lock_data = await self.db.read_table(
            "locked_channels", start_row=lock_rows[0], start_col=1, num_cols=3
        )
        _, overwrites_json, original_reason = lock_data

        # Deserialize overwrites from JSON
        serializable_overwrites = json.loads(overwrites_json)
        original_overwrites = {
            inter.guild.get_role(int(target_id))
            or inter.guild.get_member(
                int(target_id)
            ): disnake.PermissionOverwrite.from_pair(
                disnake.Permissions(pair[0]), disnake.Permissions(pair[1])
            )
            for target_id, pair in serializable_overwrites.items()
        }

        await inter.channel.edit(
            overwrites=original_overwrites,
            reason=f"Unlock command by {inter.author}",
        )

        await self.db.delete_rows("locked_channels", lock_rows)

        embed = disnake.Embed(
            title=f"{self.UNLOCKED_EMOJI} Channel Unlocked",
            description=f"Locking reason: {disnake.utils.escape_markdown(original_reason)}",
            color=self.colors.get("green", 0x78B159),
        )
        embed.set_author(name=str(inter.author), icon_url=str(inter.author.avatar.url))
        await inter.followup.send(embed=embed)

    @commands.slash_command(
        name="logging",
        description="Change the amount of logging",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @commands.guild_only()
    @logger
    async def logging(
        self,
        inter: disnake.ApplicationCommandInteraction,
        level: int = commands.Param(
            description="Logging level (0-5, 0 for all logging)",
            min_value=0,
            max_value=5,
        ),
    ):
        logger.logging_level = level
        await inter.response.send_message(
            f"Logging level set to {level}", ephemeral=True
        )

    @commands.slash_command(name="code", description="get code")
    @commands.guild_only()
    async def code(self, inter: disnake.ApplicationCommandInteraction):
        if inter.author.id not in self.admin_user_ids:
            await inter.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return
        else:
            otp = await Website.get_otp_code()
            await inter.response.send_message(
                f"Your one-time code is: {otp}", ephemeral=True
            )


def setup(bot):
    bot.add_cog(ModerationCog(bot, bot.db, bot.config))
