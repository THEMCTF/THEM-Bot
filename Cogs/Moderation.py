import os
import time
from datetime import datetime, timedelta, timezone

import disnake
import yaml
from disnake.ext import commands

# --- Configuration Loading ---
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "..", "config.yml")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    config = yaml.safe_load(f)
    MODERATOR_ROLE_IDS = config.get("moderator_roles", [])
    COLORS = config.get("colors", {})
    COLOR_RED = COLORS.get("red", 0xDD2E44)
    COLOR_GREEN = COLORS.get("green", 0x78B159)


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_purge_timestamp: float = 0
        self.locked_channels: dict[int, dict] = {}

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

        # TODO: get from config
        await inter.channel.send(
            "<:purge:1422343889100083200><:purgy:1422343933220093952>"
        )

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
    @Logger
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @commands.guild_only()
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
    @Logger
    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.guild_only()
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
    @Logger
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
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
    @Logger
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
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
            await user.ban(reason=reason)
            await inter.response.send_message(
                f"{user.mention} has been banned\nReason: {reason}"
            )

        except disnake.Forbidden:
            await inter.response.send_message(
                "I don't have permission to ban this user", ephemeral=True
            )
        except disnake.HTTPException as e:
            await inter.response.send_message(
                f"Failed to ban user: {e}", ephemeral=True
            )

    @commands.slash_command(
        name="lock",
        description="Lock the channel",
        default_member_permissions=disnake.Permissions(manage_channels=True),
    )
    @Logger
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def lock(
        self,
        inter: disnake.ApplicationCommandInteraction,
        reason: str = commands.Param(description="Reason"),
    ):
        await inter.response.defer(ephemeral=True)

        # save it so we don't perma lock it
        self.locked_channels[inter.channel.id] = {
            "overwrites": {
                target: overwrite.copy()
                for target, overwrite in inter.channel.overwrites.items()
            },
            "reason": reason,
        }

        # make it so @everyone can't send messages
        everyone_overwrite = inter.channel.overwrites_for(inter.guild.default_role)
        everyone_overwrite.send_messages = False
        await inter.channel.set_permissions(
            inter.guild.default_role, overwrite=everyone_overwrite
        )

        # make it so only @moderators and @admins can send messages
        for target, overwrite in inter.channel.overwrites.items():
            if isinstance(target, disnake.Role) and target.id not in MODERATOR_ROLE_IDS:
                overwrite.send_messages = False
                await inter.channel.set_permissions(target, overwrite=overwrite)

        embed = disnake.Embed(
            title="🔒 Channel Locked",
            description=disnake.utils.escape_markdown(str(reason)),
            color=COLOR_RED,
        )
        embed.set_author(
            name=str(inter.author),  # starry does string safety for the first time /s
            icon_url=str(inter.author.avatar.url),
        )

        await inter.followup.send(embed=embed)

    @commands.slash_command(
        name="unlock",
        description="Unlock the channel",
        default_member_permissions=disnake.Permissions(manage_channels=True),
    )
    @Logger
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def unlock(
        self,
        inter: disnake.ApplicationCommandInteraction,
    ):
        await inter.response.defer(ephemeral=True)

        lock_data = self.locked_channels.pop(inter.channel.id, None)

        if lock_data is None:
            await inter.followup.send(
                "This channel was not locked by me or has already been unlocked.",
                ephemeral=True,
            )
            return

        original_overwrites = lock_data["overwrites"]
        original_reason = lock_data.get("reason", "No reason provided.")

        await inter.channel.edit(
            overwrites=original_overwrites,
            reason=f"Unlock command by {inter.author}",
        )

        embed = disnake.Embed(
            title="🔓 Channel Unlocked",
            description=f"Locking reason: {disnake.utils.escape_markdown(original_reason)}",  # lol I found a new function
            color=COLOR_GREEN,
        )
        embed.set_author(name=str(inter.author), icon_url=str(inter.author.avatar.url))
        await inter.followup.send(embed=embed)


def setup(bot):
    bot.add_cog(ModerationCog(bot))
