import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class TicketCog(commands.Cog):
    def __init__(self, bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.solution_emoji = config.get("solution_emoji", "✅")

    async def _add_solution_(self, channel_id, message, marked_by):
        if "solutions" not in await self.db.list_tables():
            await self.db.create_table(
                "solutions",
                [
                    ("channel_id", "BIGINT"),
                    ("message_id", "BIGINT"),
                    ("marked_by", "BIGINT"),
                    ("timestamp", "TIMESTAMP"),
                ],
            )

        await self.db.add_to_table(
            "solutions",
            [
                channel_id,
                message.id,
                marked_by,
                message.created_at,
            ],
            start_row="next",
            direction="row",
        )

    async def _get_solutions_(self, channel_id):
        if "solutions" not in await self.db.list_tables():
            return FileNotFoundError("No solutions table found")

        solutions = await self.db.find_rows(
            "solutions",
            column_name="channel_id",
            value=channel_id,
        )
        # just return the message ids
        return [row["message_id"] for row in solutions]

    # TODO: make it select which challenge it's for
    @commands.message_command(
        name="Solution",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @Logger
    async def mark_solution(
        self, inter: disnake.ApplicationCommandInteraction, message: disnake.Message
    ):
        # Check if channel is in the correct category
        if inter.channel.category_id != self.config.get("ticket_category_id"):
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            await self._add_solution_(
                channel_id=inter.channel.id,
                message=message,
                marked_by=inter.author.id,
            )

            # Create a cleaner message reference
            jump_url = message.jump_url
            await inter.response.send_message(
                f"{self.solution_emoji} Marked [this message]({jump_url}) as solution",
                ephemeral=True,
            )

        except Exception as e:
            await inter.response.send_message(
                f"Failed to mark solution: {str(e)}", ephemeral=True
            )

    @commands.slash_command(
        name="solutions",
        description="Get the solutions in this channel",
        default_member_permissions=disnake.Permissions(manage_messages=True),
    )
    @Logger
    async def get_solutions(self, inter: disnake.ApplicationCommandInteraction):
        # Check if channel is in the correct category
        if inter.channel.category_id != self.config.get("ticket_category_id"):
            await inter.response.send_message(
                "This command can only be used in the ticket category", ephemeral=True
            )
            return

        try:
            solutions = await self._get_solutions_(channel_id=inter.channel.id)

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

    # TODO: Make our own ticket system


def setup(bot):
    bot.add_cog(TicketCog(bot, bot.db, bot.config))
