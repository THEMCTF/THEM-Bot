# import json

import time
from datetime import timedelta

import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="purge", description="purgey purgey")
    async def purge(self, inter: disnake.ApplicationCommandInteraction, time):
        await inter.response.send_message("YOOOO")
        await Logger.log_action(
            self,
            text=f"**/purge** was ran with the content: *{time}*",
            color=disnake.Colour.red(),
            type="Moderation",
            user=inter.author,
        )

    @commands.slash_command(
        name="timeout",
        description="Time a user out (in minutes)",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    async def timeout(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User,
        time: int,
        reason: str,
    ):
        await user.timeout(duration=timedelta(minutes=time), reason=reason)
        await inter.response.send_message(
            f"{user} has been timed out for {time}m; reason: {reason}"
        )
        await Logger.log_action(
            self,
            text=f"**/timeout** was ran with the content: *user: {user.mention}, time: {time}m, reason: {reason}*",
            color=disnake.Colour.red(),
            type="Moderation",
            user=inter.author,
        )


def setup(bot):
    bot.add_cog(ModerationCog(bot))
