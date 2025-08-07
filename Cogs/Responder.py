import disnake
from disnake.ext import commands


class MessageResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        # Ignore messages from bots unless explicitly handling them.
        if message.author.bot:
            return

        # Check for a specific message.
        if "them" in message.content.lower():
            await message.channel.send("<:THEM:1400018402059485224> :on: :top:")
            print(f"\033[34m{message.author.display_name} just said 'them'\033[0m")

        # # Check if the bot MEE6 sent a message.
        # if message.author.id == 159985870458322944 and "level" in message.content.lower():
        #     # and "level" in message.content.lower()
        #     await message.channel.send("Shut up <@159985870458322944>!")

        # if any(keyword in message.content.lower() for keyword in ["suicide", "kill", "kys", "kym", "unalive", "harm myself", "hurt myself"]) and message.author.bot == False:
        #     await message.channel.send("If you are feeling hopeless or having no reason to live. Call 988 or go to <https://988lifeline.org> to talk to someone. If you leave this world, there will always be atleast one person who will miss you. We will miss you.")
        #     # await message.channel.send("a")
        #     print(f"\033[34m{message.author.display_name} has been directed to 988\033[0m")


def setup(bot):
    bot.add_cog(MessageResponder(bot))
