import os
import subprocess

import disnake
from disnake.ext import commands

from Modules.Logger import Logger


class CTFSheet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(name="update", description="update the google sheet.")
    async def update(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(
            with_message="Running, this might take a second", ephemeral=False
        )

        try:
            # Save current directory
            original_dir = os.getcwd()
            os.chdir("/Users/starry/Desktop/Code/THEMc/Project-Onjer")

            try:
                process = subprocess.run(
                    ["python3", "main.py"],
                    capture_output=True,
                    text=True,
                )

                response = (
                    process.stdout
                    if process.returncode == 0
                    else f"Error running script:\n{process.stderr}"
                )
                success = process.returncode == 0
            except Exception as e:
                response = (
                    f"Exception while running script:\n{type(e).__name__}: {str(e)}"
                )
                success = False

            os.chdir(original_dir)

        except Exception as e:
            response = f"Directory Error:\n{type(e).__name__}: {str(e)}"
            success = False

        embed = disnake.Embed(
            title="Sheet updated" if success else "An error was encountered",
            description=response,
            color=disnake.Colour.green() if success else disnake.Colour.red(),
        )

        await inter.edit_original_message(embed=embed)
        await Logger.log_action(
            self,
            text=f"**/update** was ran {'successfully' if success else 'with errors'}",
            color=disnake.Colour.green() if success else disnake.Colour.red(),
            type="CTFSheet",
            user=inter.author,
        )


def setup(bot):
    bot.add_cog(CTFSheet(bot))
