import enum
from datetime import datetime, timedelta

import disnake
from disnake.ext import commands


# Fallback enums if disnake doesn't expose them
class _FallbackEntityType(enum.IntEnum):
    stage_instance = 1
    voice = 2
    external = 3


class _FallbackPrivacyLevel(enum.IntEnum):
    guild_only = 2


# Helper to get the "real" enum from disnake if present, else fallback
def get_entity_type(external: bool):
    ent_cls = getattr(disnake, "GuildScheduledEventEntityType", None)
    if ent_cls is not None:
        return ent_cls.external if external else ent_cls.voice
    return _FallbackEntityType.external if external else _FallbackEntityType.voice


def get_privacy_level():
    priv_cls = getattr(disnake, "GuildScheduledEventPrivacyLevel", None)
    if priv_cls is not None:
        return priv_cls.guild_only
    return _FallbackPrivacyLevel.guild_only


class Starry(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="pinthread", description="Pin the thread")
    async def pinthread(
        self,
        inter: disnake.ApplicationCommandInteraction,
        thread_id: int = commands.Param(
            None, description="ID of the thread to pin (optional)"
        ),
    ):
        if inter.author.id != 733839959009525761:
            await inter.response.send_message("WIP")

        await inter.response.defer()

        # Determine thread to pin
        if thread_id is None:
            if isinstance(inter.channel, disnake.Thread):
                thread = inter.channel
            else:
                await inter.followup.send(
                    "You must provide a thread ID or run this inside a thread."
                )
                return
        else:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(
                thread_id
            )

        if not isinstance(thread, disnake.Thread):
            await inter.followup.send("That is not a thread channel.")
            return

        try:
            await thread.edit(pinned=True)
            await inter.followup.send(f"Thread '{thread.name}' has been pinned.")
            print(
                f"\033[34m{inter.author.display_name} pinned thread '{thread.name}'\033[0m"
            )
        except disnake.Forbidden:
            await inter.followup.send("I don't have permission to pin this thread.")
        except Exception as e:
            await inter.followup.send(f"Error pinning thread: {e}")

    @commands.install_types(user=True)
    @commands.slash_command(
        name="testing", description="this command is subject to change"
    )
    async def testing(self):
        bot = self.bot
        # List all servers the bot is in
        if 1 == 2:
            for guild in bot.guilds:
                print(f"\nServer: {guild.name} (ID: {guild.id})")

                # Try to fetch existing invites
                try:
                    invites = await guild.invites()
                    if invites:
                        for invite in invites:
                            print(f"Invite: {invite.url}")
                    else:
                        # Create a temporary invite if none exist
                        if guild.me.guild_permissions.create_instant_invite:
                            invite = await guild.text_channels[0].create_invite(
                                max_age=3600, max_uses=1
                            )
                            print(f"Generated invite: {invite.url}")
                        else:
                            print("No invites found and cannot create one.")
                except disnake.Forbidden:
                    print("Bot does not have permission to view invites.")


def setup(bot):
    bot.add_cog(Starry(bot))
