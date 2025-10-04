import time
from datetime import datetime, timedelta, timezone

import disnake
from disnake.ext import commands

from Modules.Database import Database  # For ticket solutions
from Modules.old.Logger import Logger


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_purge_timestamp: float = 0

    async def _perform_purge(
        self,
        inter: disnake.ApplicationCommandInteraction,
        response_type: str = "default",
        user: disnake.User = None,
        **purge_kwargs,
    ):
        """
        A helper function to perform message purging, handle exceptions, and send responses.

        Args:
            inter: The interaction to respond to.
            response_type: The type of response to send ('default' or 'from_message').
            user: The user whose messages are being purged (for response formatting).
            **purge_kwargs: Keyword arguments to pass to `channel.purge()`.
        """
        try:
            # If a user is specified for a standard purge, we need to collect messages manually
            # to ensure we delete the correct number of messages from that user.
            if user and response_type == "default":
                messages_to_delete = []
                limit = purge_kwargs.get("limit", 100)
                async for message in inter.channel.history(
                    limit=limit * 5
                ):  # Search more to find user's messages
                    if len(messages_to_delete) >= limit:
                        break
                    if message.author.id == user.id:
                        messages_to_delete.append(message)

                if not messages_to_delete:
                    deleted = []
                else:
                    # bulk_delete is not a method on TextChannel, use delete_messages instead.
                    await inter.channel.delete_messages(messages_to_delete)
                    deleted = messages_to_delete  # The return value is None, so we use our list.
            else:
                deleted = await inter.channel.purge(**purge_kwargs)

            # Send public emoji confirmation if not on cooldown
            current_time = time.time()
            if current_time - self._last_purge_timestamp > 180:  # 3 minutes
                await inter.channel.send(
                    "<:purge:1422343889100083200><:purgy:1422343933220093952>"
                )
                self._last_purge_timestamp = current_time

            # Send ephemeral confirmation
            if response_type == "default":
                msg = f"Deleted {len(deleted)} message(s)"
                if user:
                    msg += f" from {str(user)}."
                await inter.followup.send(msg, ephemeral=True)
            else:  # from_message
                await inter.followup.send(
                    f"Deleted {len(deleted)} message(s).", ephemeral=True
                )

        except disnake.Forbidden:
            await inter.followup.send(
                "I don't have permission to delete messages.", ephemeral=True
            )
        except disnake.HTTPException as e:
            await inter.followup.send(f"Failed to delete messages: {e}", ephemeral=True)

    @commands.slash_command(
        name="purge",
        description="Delete multiple messages at once",
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
    ):
        await inter.response.defer(ephemeral=True)

        # Check if amount is valid
        if amount < 1 or amount > 1000:
            await inter.followup.send(
                "Please specify a number between 1 and 1,000", ephemeral=True
            )
            return

        # Create check function if user is specified
        def check(msg):
            return user is None or msg.author.id == user.id

        # Delete messages
        await self._perform_purge(inter, user=user, limit=amount, check=check)

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
        """Deletes the selected message and all messages below it."""
        await inter.response.defer(ephemeral=True)

        # Purge messages after the target message, including the message itself.
        # The `after` parameter is exclusive, so we find messages sent after the
        # target message's creation time.
        await self._perform_purge(
            inter,
            response_type="from_message",
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
                f"Failed to timeout user: {str(e)}", ephemeral=True
            )

    # TODO: make it select which challenge it's for
    @commands.message_command(name="Solution")
    @Logger
    async def mark_solution(
        self, inter: disnake.ApplicationCommandInteraction, message: disnake.Message
    ):
        # Check if channel is in the correct category
        if inter.channel.category_id != 1385339846117294110:
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            await Database.add_solution(
                channel_id=inter.channel.id,
                message_id=message.id,
                user_id=message.author.id,
                marked_by=inter.author.id,
            )

            # Create a cleaner message reference
            jump_url = message.jump_url
            await inter.response.send_message(
                f"✅ Marked [this message]({jump_url}) as solution",
                ephemeral=True,
            )

        except Exception as e:
            await inter.response.send_message(
                f"Failed to mark solution: {str(e)}", ephemeral=True
            )

    @commands.slash_command(
        name="solutions",
        description="Get the solutions in this channel",
    )
    @Logger
    async def get_solutions(self, inter: disnake.ApplicationCommandInteraction):
        # Check if channel is in the correct category
        if inter.channel.category_id != 1385339846117294110:
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            solutions = await Database.get_solutions(channel_id=inter.channel.id)

            if not solutions:
                await inter.response.send_message(
                    "No solutions have been marked yet", ephemeral=True
                )
                return

            # Format solutions nicely
            messages = []
            for solution in solutions:
                channel = inter.channel
                message = await channel.fetch_message(solution["message_id"])
                if message:
                    message_link = f"https://discord.com/channels/{inter.guild.id}/{channel.id}/{message.id}"
                    messages.append(f"[{message.content}]({message_link})")

            solutions_text = "\n".join(f"• {msg}" for msg in messages)

            await inter.response.send_message(
                f"**Solutions in this channel:**\n{solutions_text}", ephemeral=True
            )

        except Exception as e:
            await inter.response.send_message(
                f"Failed to get solutions: {str(e)}", ephemeral=True
            )


def setup(bot):
    bot.add_cog(ModerationCog(bot))
