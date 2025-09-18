import datetime
import os
import subprocess

import disnake
from disnake import TextInputStyle
from disnake.ext import commands
from disnake.ui import Modal, StringSelect, TextInput, View

from Modules.Logger import Logger


# Create a separate view for the select component
class CTFSelectView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout

    @disnake.ui.string_select(
        placeholder="Choose challenge types...",
        min_values=1,
        max_values=6,  # Allow multiple selections
        options=[
            disnake.SelectOption(label="Reverse Engineering", value="rev", emoji="🔧"),
            disnake.SelectOption(label="Web", value="web", emoji="🌐"),
            disnake.SelectOption(label="OSINT", value="osint", emoji="🔍"),
            disnake.SelectOption(label="Cryptography", value="crypto", emoji="🔐"),
            disnake.SelectOption(label="Forensics", value="forensics", emoji="🔎"),
            disnake.SelectOption(label="Pwn", value="pwn", emoji="💥"),
        ],
    )
    async def select_callback(self, select, interaction):
        # Store the selected values for later use
        self.selected_types = select.values

        # Create and send the modal
        modal = CTFModal(self.selected_types)
        await interaction.response.send_modal(modal)


# Subclassing the modal - modals can only contain TextInput components
class CTFModal(disnake.ui.Modal):
    def __init__(self, selected_types=None):
        self.selected_types = selected_types or []

        components = [
            TextInput(
                label="CTF name (Do not include year)",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            TextInput(
                label="CTF start time (YYYY-MM-DD HH:MM, UTC)",
                custom_id="start",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            TextInput(
                label="CTF end time (YYYY-MM-DD HH:MM, UTC)",
                custom_id="end",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            TextInput(
                label="More categories (separate with semicolon ;)",
                custom_id="cats",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="e.g. steganography;blockchain",
                max_length=200,
            ),
            TextInput(
                label="Discord Server (invite link or server name)",
                custom_id="discord",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="https://discord.gg/...",
                max_length=200,
            ),
            TextInput(
                label="Website URL",
                custom_id="website",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="https://ctf.example.com",
                max_length=200,
            ),
            TextInput(
                label="Additional Notes",
                custom_id="notes",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                placeholder="Any additional information about the CTF...",
                max_length=1000,
            ),
        ]

        super().__init__(
            title="CTF Registration Form",
            components=components,
            timeout=900,  # 15 minute timeout
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Get values from the modal
            ctf_name = (
                inter.text_values.get("name", "")
                .strip()
                .append(datetime.datetime.now().year)
            )
            # format the start and end to unix time
            start_str = inter.text_values.get("start", "").strip()
            end_str = inter.text_values.get("end", "").strip()
            try:
                start_time = int(
                    datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M").timestamp()
                )
                end_time = int(
                    datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M").timestamp()
                )
            await inter.response.send_message(
                    "❌ Invalid date format. Please use YYYY-MM-DD HH:MM (UTC).",
                    ephemeral=True,
                )

            more_cats = inter.text_values.get("cats", "").strip()
            discord_server = inter.text_values.get("discord", "").strip()
            website = inter.text_values.get("website", "").strip()
            notes = inter.text_values.get("notes", "").strip()

            # Process additional categories
            additional_categories = (
                [cat.strip() for cat in more_cats.split(";") if cat.strip()]
                if more_cats
                else []
            )

            # Combine selected types with additional categories
            all_categories = self.selected_types + additional_categories

            # Create response embed
            embed = disnake.Embed(
                title=f"🚩 CTF Registration: {ctf_name}",
                color=disnake.Color.blue(),
                timestamp=inter.created_at,
            )

            # Add fields to embed
            if all_categories:
                embed.add_field(
                    name="📋 Challenge Categories",
                    value=", ".join(f"`{cat}`" for cat in all_categories),
                    inline=False,
                )

            if discord_server:
                embed.add_field(
                    name="💬 Discord Server", value=discord_server, inline=True
                )

            if website:
                embed.add_field(name="🌐 Website", value=website, inline=True)

            if notes:
                embed.add_field(name="📝 Additional Notes", value=notes, inline=False)

            embed.set_footer(text=f"Registered by {inter.author.display_name}")

            try:
                await CTFSheet.make_role(name=ctf_name)
                await CTFSheet.make_ctf_channel(
                    guild=inter.guild,
                    channel_name=ctf_name.lower().replace(" ", "-"),
                    allowed_role=disnake.utils.get(inter.guild.roles, name=ctf_name),
                )
                await CTFSheet.make_forum_channel(
                    guild=inter.guild,
                    channel_name=f"{ctf_name}",
                    tags=[", ".join(f"`{cat}`" for cat in all_categories)],
                    perms={
                        disnake.utils.get(
                            inter.guild.roles, name=ctf_name
                        ): disnake.PermissionOverwrite(view_channel=True)
                    },
                )
            except Exception as e:
                print(f"Error creating role/channel/forum: {e}")
            await inter.response.send_message(embed=embed, ephemeral=True)

            # Log the CTF registration (assuming Logger is properly set up)
            try:
                Logger.info(
                    f"CTF registered: {ctf_name} by {inter.author} ({inter.author.id})"
                )
            except Exception as e:
                print(f"Logging error: {e}")

        except Exception as e:
            await inter.response.send_message(
                f"❌ An error occurred while processing your CTF registration: {str(e)}",
                ephemeral=True,
            )
            print(f"Modal callback error: {e}")


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

    @commands.slash_command(
        name="register_ctf", description="Register a new CTF competition"
    )
    async def register_ctf(self, inter: disnake.ApplicationCommandInteraction):
        """Command to start CTF registration process"""
        view = CTFSelectView()

        embed = disnake.Embed(
            title="🚩 CTF Registration",
            description="First, select the challenge types that will be available in this CTF:",
            color=disnake.Color.green(),
        )

        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    async def make_role(
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        color: disnake.Color = disnake.Color.default(),
        hoist: bool = False,
        mentionable: bool = False,
        permissions: disnake.Permissions = disnake.Permissions.none(),
    ):
        """
        Creates a new role in the server.

        Parameters
        ----------
        name: The name of the role.
        color: The color of the role (optional, defaults to default color).
        hoist: Whether the role should be displayed separately in the member list (optional, defaults to False).
        mentionable: Whether the role can be mentioned by anyone (optional, defaults to False).
        permissions: The permissions for the role (optional, defaults to no permissions).
        """
        target_role = 1382763556642099242
        if inter.author.guild_permissions.manage_roles:
            try:
                # Get the position of the target role
                target_role_position = target_role.position

                # Calculate the position for the new role (one less than the target role)
                new_role_position = target_role_position - 1

                await inter.response.send_message(
                    f"Created role '{new_role.name}' below '{target_role.name}'."
                )
                new_role = await inter.guild.create_role(
                    name=name,
                    color=color,
                    hoist=hoist,
                    mentionable=mentionable,
                    permissions=permissions,
                    position=new_role_position,
                )
                await inter.response.send_message(
                    f"Role '{new_role.name}' created successfully!"
                )
            except disnake.Forbidden:
                await inter.response.send_message(
                    "I don't have permission to create roles.", ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(
                    f"An error occurred: {e}", ephemeral=True
                )
        else:
            await inter.response.send_message(
                "You don't have permission to create roles.", ephemeral=True
            )

    async def make_ctf_channel(
        guild: disnake.Guild, channel_name: str, allowed_role: disnake.Role
    ):
        # 1. Define permission overwrites for the @everyone role
        everyone_overwrite = disnake.PermissionOverwrite(view_channel=False)

        # 2. Define permission overwrites for roles that should have access
        allowed_role_overwrite = disnake.PermissionOverwrite(view_channel=True)

        # 3. Get the other role by ID
        other_role = guild.get_role(1382763556792963102)

        # 4. Create overwrites dictionary
        overwrites = {
            guild.default_role: everyone_overwrite,
            allowed_role: allowed_role_overwrite,
        }

        # Add the other role if it exists
        if other_role:
            overwrites[other_role] = allowed_role_overwrite

        # 5. Create the text channel
        try:
            new_channel = await guild.create_text_channel(
                name=channel_name, overwrites=overwrites
            )
            print(
                f"Created private channel: {new_channel.name} with access for {allowed_role.name}"
            )
            return new_channel
        except disnake.HTTPException as e:
            print(f"Error creating channel: {e}")
            return None

    async def make_forum_channel(
        guild: disnake.Guild, channel_name: str, tags: list[dict], perms: dict
    ):
        """
        Create a forum channel with specified name, tags, and permissions.

        Args:
            guild: The Discord guild to create the channel in
            channel_name: Name of the forum channel
            tags: List of tag dictionaries with 'name' and optionally 'emoji' keys
                Example: [{"name": "Bug Report", "emoji": "🐛"}, {"name": "Feature Request"}]
            perms: Dictionary mapping role IDs/role objects to permission overwrites
                Example: {guild.default_role: PermissionOverwrite(view_channel=False)}
        """

        try:
            # Create the forum channel first
            forum_channel = await guild.create_forum_channel(
                name=channel_name, overwrites=perms
            )

            # Create forum tags
            forum_tags = []
            for tag_data in tags:
                tag_name = tag_data.get("name")
                tag_emoji = tag_data.get("emoji")

                if tag_name:
                    # Create ForumTag object
                    if tag_emoji:
                        forum_tag = disnake.ForumTag(name=tag_name, emoji=tag_emoji)
                    else:
                        forum_tag = disnake.ForumTag(name=tag_name)
                    forum_tags.append(forum_tag)

            # Edit the channel to add the tags
            if forum_tags:
                await forum_channel.edit(available_tags=forum_tags)

            print(
                f"Created forum channel: {forum_channel.name} with {len(forum_tags)} tags"
            )
            return forum_channel

        except disnake.HTTPException as e:
            print(f"Error creating forum channel: {e}")
            return None


def setup(bot):
    bot.add_cog(CTFSheet(bot))
