from datetime import timedelta

import disnake
from disnake.ext import commands

from Modules import log
from Modules.Database import Database  # For ticket solutions


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @log(text="Purge command was used", color=0xFF0000)
    @commands.slash_command(
        name="purge",
        description="Delete multiple messages at once",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
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
        try:
            deleted = await inter.channel.purge(
                limit=amount,
                check=check,
            )

            msg = f"Deleted {len(deleted)} message(s)"
            if user:
                msg += f" from {user.mention}"

            await inter.followup.send(msg, ephemeral=True)

        except disnake.Forbidden:
            await inter.followup.send(
                "I don't have permission to delete messages", ephemeral=True
            )

    @log(text="Purge (context menu) command was used", color=0xFF0000)
    @commands.message_command(
        name="purge",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.guild_only()
    async def purge_from_message(
        self,
        inter: disnake.ApplicationCommandInteraction,
        message: disnake.Message,
    ):
        """Deletes the selected message and all messages below it."""
        await inter.response.defer(ephemeral=True)

        try:
            # Purge messages after the target message, including the message itself.
            # The `before` parameter is exclusive, so we find messages sent after the
            # target message's creation time.
            deleted = await inter.channel.purge(
                limit=None,  # No limit, purge all applicable
                after=message.created_at - timedelta(microseconds=1),
                oldest_first=False,  # Not strictly necessary, but can be slightly more efficient
            )

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
        name="timeout",
        description="Time a user out",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    @log(text="Timeout command was used", color=0xFF0000)
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
    @log(text="Solution marked", color=0x00FF00)
    @commands.message_command(name="Solution")
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

    @log(text="Solution count requested", color=0x00FF00)
    @commands.slash_command(
        name="solutions",
        description="Get the solutions in this channel",
    )
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
