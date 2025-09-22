import asyncio
import logging
import os
from typing import Optional

import disnake
from disnake.ext import commands, tasks

from Modules.Database import Database


class ChangelogUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_content: Optional[str] = None
        self.check_changelog.start()
        self.logger = logging.getLogger(__name__)

    def cog_unload(self):
        self.check_changelog.cancel()

    @tasks.loop(minutes=5)
    async def check_changelog(self):
        try:
            # Read current changelog
            changelog_path = os.path.join(os.path.dirname(__file__), "../changelog.md")
            with open(changelog_path, "r") as f:
                current_content = f.read()

            # If this is the first run, just store the content
            if self._last_content is None:
                self._last_content = current_content
                try:
                    await Database.update_changelog_history(current_content)
                except Exception as e:
                    self.logger.error(f"Failed to update changelog history: {e}")
                return

            # Check if content has changed
            if current_content != self._last_content:
                # Get all subscribers
                try:
                    subscriber_ids = await Database.get_changelog_subscribers()
                except Exception as e:
                    self.logger.error(f"Failed to get subscribers: {e}")
                    subscriber_ids = []

                # Create notification embed
                embed = disnake.Embed(
                    title="🔄 Changelog Updated!",
                    description=f"```md\n{current_content}\n```",
                    color=0x00FF00,
                )

                # Notify all subscribers
                for user_id in subscriber_ids:
                    try:
                        user = await self.bot.get_or_fetch_user(user_id)
                        if user:
                            await user.send(embed=embed)
                    except Exception as e:
                        self.logger.error(f"Failed to notify user {user_id}: {e}")

                # Update stored content
                self._last_content = current_content
                try:
                    await Database.update_changelog_history(current_content)
                except Exception as e:
                    self.logger.error(f"Failed to update changelog history: {e}")

        except Exception as e:
            self.logger.error(f"Error in changelog monitor: {e}")

    @check_changelog.before_loop
    async def before_check_changelog(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(ChangelogUpdater(bot))
