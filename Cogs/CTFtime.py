import datetime

import disnake
import requests
from disnake.ext import commands


class CTFtimeAPI(commands.Cog):
    """Cog for fetching upcoming CTF events from CTFtime"""  # comments be like: [shocked]

    def __init__(self, bot):
        self.bot = bot

    def get_events(self, start: int, finish: int = "", limit: int = 10):
        """Fetch events from CTFtime API"""
        url = "https://ctftime.org/api/v1/events/"
        params = {"limit": limit, "start": start}
        if finish:
            params["finish"] = finish

        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    @commands.slash_command(name="upcoming", description="Gets the upcoming CTFs")
    async def upcoming(self, inter, index: int = 0):
        """Check upcoming events (like Discord.js version)"""
        now = int(datetime.datetime.now().timestamp())

        try:
            events = self.get_events(now, "", 10)

            if not events:
                await inter.response.send_message(
                    "No upcoming CTFs found!", mention_author=True
                )
                return

            if index < 0:
                await inter.response.send_message(
                    "Invalid index given", mention_author=True
                )
                return

            if index >= len(events):
                await inter.response.send_message(
                    f"There are only {len(events)} upcoming events. Please choose an index below {len(events)}.",
                    mention_author=True,
                )
                return

            cur_event = events[index]

            # embed
            embed = disnake.Embed(
                title=cur_event.get("title", "Untitled Event"),
                url=cur_event.get("ctftime_url", ""),
                description=cur_event.get("description", "No description provided."),
                color=disnake.Color.red(),
            )

            if cur_event.get("logo"):
                embed.set_thumbnail(url=cur_event["logo"])

            embed.add_field(
                name="Format", value=cur_event.get("format", "N/A"), inline=True
            )
            embed.add_field(name="Link", value=cur_event.get("url", "N/A"), inline=True)
            embed.add_field(
                name="CTFTime URL",
                value=cur_event.get("ctftime_url", "N/A"),
                inline=False,
            )

            # timestamps
            start_time = datetime.datetime.fromisoformat(
                cur_event["start"].replace("Z", "+00:00")
            )
            finish_time = datetime.datetime.fromisoformat(
                cur_event["finish"].replace("Z", "+00:00")
            )
            embed.add_field(
                name="Start",
                value=start_time.strftime("%b %d %Y %I:%M %p %Z"),
                inline=True,
            )
            embed.add_field(
                name="Finish",
                value=finish_time.strftime("%b %d %Y %I:%M %p %Z"),
                inline=True,
            )

            await inter.response.send_message(embed=embed)

        except Exception as e:
            await inter.response.send_message(
                f"Error getting events: {e}", mention_author=True
            )


def setup(bot):
    bot.add_cog(CTFtimeAPI(bot))
