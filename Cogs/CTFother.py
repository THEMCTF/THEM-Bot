import datetime
import os
import subprocess

import disnake
from disnake import TextInputStyle
from disnake.ext import commands
from disnake.ui import Modal, StringSelect, TextInput, View

from Modules.Logger import Logger

# global ctf_end_time


# Create a separate view for the select component
class CTFSelectView(disnake.ui.View):
    """View containing the select dropdown for CTF challenge types."""

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
        """Handle selection of CTF challenge types."""
        # Store the selected values for later use
        self.selected_types = select.values

        # Create and send the modal
        modal = CTFModal(self.selected_types)
        await interaction.response.send_modal(modal)


# Subclassing the modal - modals can only contain TextInput components
class CTFModal(disnake.ui.Modal):
    """Modal form for CTF registration details."""

    def __init__(self, selected_types=None):
        """Initialize modal with selected challenge types."""
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
                label="Website URL",
                custom_id="website",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="https://ctf.example.com",
                max_length=200,
            ),
        ]

        super().__init__(
            title="CTF Registration Form",
            components=components,
            timeout=900,  # 15 minute timeout
        )

    async def callback(self, inter: disnake.ModalInteraction):
        """Process the submitted CTF registration form."""
        try:
            # Get values from the modal
            ctf_name_input = inter.text_values.get("name", "").strip()
            current_year = datetime.datetime.now().year
            ctf_name = f"{ctf_name_input} {current_year}"

            # Format the start and end to unix time
            start_str = inter.text_values.get("start", "").strip()
            end_str = inter.text_values.get("end", "").strip()

            try:
                start_time = int(
                    datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M").timestamp()
                )
                end_time = int(
                    datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M").timestamp()
                )
                if end_time <= start_time:
                    await inter.response.send_message(
                        "❌ End time must be after start time.", ephemeral=True
                    )
                    return
                global ctf_end_time
                ctf_end_time = end_time
            except ValueError:
                await inter.response.send_message(
                    "❌ Invalid date format. Please use YYYY-MM-DD HH:MM (UTC).",
                    ephemeral=True,
                )
                return

            more_cats = inter.text_values.get("cats", "").strip()
            website = inter.text_values.get("website", "").strip()

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

            # Add time fields
            embed.add_field(
                name="⏰ Start Time", value=f"<t:{start_time}:F>", inline=True
            )
            embed.add_field(name="⏰ End Time", value=f"<t:{end_time}:F>", inline=True)

            # Add fields to embed
            if all_categories:
                embed.add_field(
                    name="📋 Challenge Categories",
                    value=", ".join(f"`{cat}`" for cat in all_categories),
                    inline=False,
                )

            if website:
                embed.add_field(name="🌐 Website", value=website, inline=True)

            embed.set_footer(text=f"Registered by {inter.author.display_name}")

            try:
                await CTFSheet.make_role(inter.guild, name=ctf_name)
                await CTFSheet.make_ctf_channel(
                    guild=inter.guild,
                    channel_name=ctf_name.lower().replace(" ", "-"),
                    allowed_role=disnake.utils.get(inter.guild.roles, name=ctf_name),
                )
                await CTFSheet.make_forum_channel(
                    guild=inter.guild,
                    channel_name=f"{ctf_name}-forum",
                    tags=[{"name": cat} for cat in all_categories],
                    perms={
                        inter.guild.default_role: disnake.PermissionOverwrite(
                            view_channel=False
                        ),
                        disnake.utils.get(
                            inter.guild.roles, name=ctf_name
                        ): disnake.PermissionOverwrite(view_channel=True),
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
    """Main cog for CTF management commands."""

    def __init__(self, bot):
        """Initialize the CTF cog."""
        self.bot = bot

    # --- Slash Commands ---
    @commands.slash_command(
        name="update",
        description="update the google sheet.",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    async def update(self, inter: disnake.ApplicationCommandInteraction):
        """Update the Google sheet by running the external script."""
        await inter.response.defer(
            with_message="Running, this might take a second", ephemeral=False
        )

        try:
            # Save current directory
            original_dir = os.getcwd()
            os.chdir("../Project-Onjer")

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
        name="register_ctf",
        description="Register a new CTF competition",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    async def register_ctf(self, inter: disnake.ApplicationCommandInteraction):
        """Start the CTF registration process with challenge type selection."""
        view = CTFSelectView()

        embed = disnake.Embed(
            title="🚩 CTF Registration",
            description="First, select the challenge types that will be available in this CTF:",
            color=disnake.Color.green(),
        )

        await inter.response.send_message(embed=embed, view=view, ephemeral=True)

    @staticmethod
    async def make_role(
        guild: disnake.Guild,
        name: str,
        color: disnake.Color = disnake.Color.default(),
        hoist: bool = False,
        mentionable: bool = False,
        permissions: disnake.Permissions = disnake.Permissions.none(),
    ):
        """Create a new role in the specified guild with given parameters."""
        """
        Creates a new role in the server.

        Parameters
        ----------
        guild: The guild to create the role in.
        name: The name of the role.
        color: The color of the role (optional, defaults to default color).
        hoist: Whether the role should be displayed separately in the member list (optional, defaults to False).
        mentionable: Whether the role can be mentioned by anyone (optional, defaults to False).
        permissions: The permissions for the role (optional, defaults to no permissions).
        """
        try:
            # Get the target role by ID
            target_role = guild.get_role(1382763556642099242)

            if target_role:
                # Calculate the position for the new role (one less than the target role)
                new_role_position = target_role.position - 1
            else:
                new_role_position = 1

            new_role = await guild.create_role(
                name=name,
                color=color,
                hoist=hoist,
                mentionable=mentionable,
                permissions=permissions,
            )

            # Move the role to the desired position
            await new_role.edit(position=new_role_position)

            print(f"Created role '{new_role.name}' successfully!")
            return new_role

        except disnake.Forbidden:
            print("Bot doesn't have permission to create roles.")
            return None
        except Exception as e:
            print(f"An error occurred creating role: {e}")
            return None

    @staticmethod
    async def make_ctf_channel(
        guild: disnake.Guild, channel_name: str, allowed_role: disnake.Role
    ):
        """Create a private text channel for the CTF with restricted access."""
        # Define permission overwrites for the @everyone role
        everyone_overwrite = disnake.PermissionOverwrite(view_channel=False)

        # Define permission overwrites for roles that should have access
        allowed_role_overwrite = disnake.PermissionOverwrite(view_channel=True)

        # Get the other role by ID
        other_role = guild.get_role(1382763556792963102)

        # Create overwrites dictionary
        overwrites = {
            guild.default_role: everyone_overwrite,
        }

        if allowed_role:
            overwrites[allowed_role] = allowed_role_overwrite

        # Add the other role if it exists
        if other_role:
            overwrites[other_role] = allowed_role_overwrite

        # Create the text channel
        try:
            new_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                position=1,
                category=1382763557816500226,
            )
            print(
                f"Created private channel: {new_channel.name} with access for {allowed_role.name if allowed_role else 'no specific role'}"
            )
            return new_channel
        except disnake.HTTPException as e:
            print(f"Error creating channel: {e}")
            return None

    @staticmethod
    async def make_forum_channel(
        guild: disnake.Guild, channel_name: str, tags: list[dict], perms: dict
    ):
        """
        Create a forum channel with specified name, tags, and permissions.

        Args:
            guild: The Discord guild to create the channel in
            channel_name: Name of the forum channel
            tags: List of tag dictionaries with 'name' and optionally 'emoji' keys
            perms: Dictionary mapping role IDs/role objects to permission overwrites
        """

        try:
            # Create the forum channel first
            forum_channel = await guild.create_forum_channel(
                name=channel_name,
                overwrites=perms,
                position=1,
                category=1382763557816500226,
            )

            # Create forum tags
            forum_tags = []
            for tag_data in tags:
                if isinstance(tag_data, dict):
                    tag_name = tag_data.get("name")
                    tag_emoji = tag_data.get("emoji")
                else:
                    # Handle case where tag_data might be a string
                    tag_name = str(tag_data)
                    tag_emoji = None

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

    # TODO: make it auto detect threads in a specific channel and if it is similar to the ctf name, then check for any messages in the thread, and whoever the author of those messages are, give them the role.
    @commands.Cog.listener()
    async def auto_assign_role(self, thread: disnake.Thread):
        """Auto-assign CTF role based on thread name."""
        try:
            # Check if the thread is in the designated channel (replace with your channel ID)
            designated_channel_id = 1382763557640470615
            if thread.parent_id != designated_channel_id:
                return

            # Check if the thread is recent
            # just check if it's been made in the past week and contains the ctf name
            if (datetime.datetime.utcnow() - thread.created_at).days > 7:
                return
            ctf_name = thread.name.split(" - ")[0].strip()

            # Find the corresponding role in the guild
            role = disnake.utils.get(thread.guild.roles, name=ctf_name)
            if not role:
                print(f"No role found for CTF: {ctf_name}")
                return

            # Assign the role to all members who have posted in the thread
            async for message in thread.history(limit=None):
                member = message.author
                if isinstance(member, disnake.Member) and role not in member.roles:
                    await member.add_roles(role)
                    print(f"Assigned role '{role.name}' to {member.display_name}")

        except Exception as e:
            print(f"Error in auto_assign_role: {e}")

    @commands.Cog.listener()
    async def on_thread_update(self, before: disnake.Thread, after: disnake.Thread):
        """Move forum and channel to 'Archive' category if the CTF has ended."""
        # Check if the thread was just closed
        if before.archived == False and after.archived == True:
            return  # We only care about threads being archived

        # Check if the CTF has ended
        ctf_end_time = getattr(after, "ctf_end_time", None)
        if ctf_end_time and ctf_end_time < datetime.datetime.utcnow():
            text_channel = disnake.utils.get(
                after.guild.text_channels, name=after.name.lower().replace(" - ", "-")
            )
            if text_channel:
                ended_category = disnake.utils.get(
                    after.guild.categories, id=1385002767382347776
                )
                if ended_category:
                    # also make it so the text channel is position 0 and the forum is position 1
                    await text_channel.edit(category=ended_category)
                    print(f"Moved channel '{text_channel.name}' to 'Archive' category")
            # get the forum channel
            forum_channel = disnake.utils.get(
                after.guild.forum_channels,
                name=after.name.lower().replace(" - ", "-") + "-forum",
            )
            if forum_channel:
                ended_category = disnake.utils.get(
                    after.guild.categories, id=1385002767382347776
                )
                if ended_category:
                    # also make it so the text channel is position 0 and the forum is position 1
                    await forum_channel.edit(category=ended_category)
                    print(f"Moved forum '{forum_channel.name}' to 'Archive' category")
            await text_channel.set_permissions(
                after.guild.default_role, view_channel=True
            )
            await forum_channel.set_permissions(
                after.guild.default_role, view_channel=True
            )


def setup(bot):
    bot.add_cog(CTFSheet(bot))
