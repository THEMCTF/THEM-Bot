import asyncio
import datetime
import os
import subprocess

import disnake
import yaml
from disnake import TextInputStyle
from disnake.ext import commands, tasks

from Modules import log
from Modules.CooldownManager import dynamic_cooldown
from Modules.Database import Database
from Modules.Logger import Logger

# --- Configuration Loading ---
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, "..", "config.yml")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    config = yaml.safe_load(f)
    ANNOUNCEMENT_CHANNEL_ID = config.get("announcements")
    CTF_PLAYER_ROLES = config.get("ctf_player_roles", [])
    ADMIN_USER_IDS = config.get("admin_user_ids", [])


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
        modal = CTFModalPart1(self.selected_types)
        await interaction.response.send_modal(modal)


# Subclassing the modal - modals can only contain TextInput components
class CTFModalPart1(disnake.ui.Modal):
    """Modal form for CTF registration details."""

    def __init__(self, selected_types=None):
        """Initialize modal with selected challenge types."""
        self.selected_types = selected_types or []

        components = [
            disnake.ui.TextInput(
                label="CTF name (Do not include year)",
                custom_id="name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="CTF start time (YYYY-MM-DD HH:MM, UTC)",
                custom_id="start",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="CTF end time (YYYY-MM-DD HH:MM, UTC)",
                custom_id="end",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Website URL",
                custom_id="website",
                style=disnake.TextInputStyle.short,
                required=True,
                placeholder="https://ctf.example.com",
                max_length=200,
            ),
        ]

        super().__init__(
            title="CTF Registration (1/2)",
            components=components,
            timeout=900,  # 15 minute timeout
        )

    async def callback(self, inter: disnake.ModalInteraction):
        """Process the first part of the form and open the second part."""
        # Respond with a button to open the next part of the form.
        # We can't send a modal in response to a modal submission.
        view = disnake.ui.View()
        view.add_item(
            disnake.ui.Button(
                label="Continue Registration",
                style=disnake.ButtonStyle.primary,
                custom_id="ctf_register_part2",
            )
        )

        await inter.response.send_message(
            "Click below to continue registration.", view=view, ephemeral=True
        )

        # Wait for the button click to open the second modal
        try:
            button_inter: disnake.MessageInteraction = await inter.bot.wait_for(
                "button_click",
                check=lambda i: i.component.custom_id == "ctf_register_part2"
                and i.author.id == inter.author.id,
                timeout=300,  # 5-minute timeout for the user to click 'Continue'
            )
            modal_part2 = CTFModalPart2(
                selected_types=self.selected_types, part1_data=inter.text_values
            )
            await button_inter.response.send_modal(modal_part2)
        except asyncio.TimeoutError:
            # The user didn't click the 'Continue' button in time.
            # We can edit the message to indicate that the registration has expired.
            await inter.edit_original_response(
                content="Registration timed out.", view=None
            )


class CTFModalPart2(disnake.ui.Modal):
    """Second part of the modal form for CTF registration."""

    def __init__(self, selected_types: list, part1_data: dict):
        """Initialize the second modal with data from the first."""
        self.selected_types = selected_types
        self.part1_data = part1_data

        components = [
            disnake.ui.TextInput(
                label="More categories (separate with semicolon ;)",
                custom_id="cats",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="e.g. steganography;blockchain",
                max_length=200,
            ),
            disnake.ui.TextInput(
                label="Team name",
                custom_id="teamname",
                style=disnake.TextInputStyle.short,
                required=True,
                placeholder="THEM?!",
                max_length=200,
            ),
            disnake.ui.TextInput(
                label="Password",
                custom_id="password",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="v3rY-S3cur3-Pa55w0rd",
                max_length=200,
            ),
            disnake.ui.TextInput(
                label="Discord",
                custom_id="discord",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="discord.gg/its-them",
                max_length=200,
            ),
            disnake.ui.TextInput(
                label="Spreadsheet",
                custom_id="sheet",
                style=disnake.TextInputStyle.short,
                required=False,
                placeholder="h",
                max_length=200,
            ),
        ]

        super().__init__(
            title="CTF Registration (2/2)",
            components=components,
            timeout=900,  # 15 minute timeout
        )

    async def callback(self, inter: disnake.ModalInteraction):
        """Process the submitted CTF registration form."""
        try:
            # Get values from the modal
            ctf_name_input = self.part1_data.get("name", "").strip()
            current_year = datetime.datetime.now().year
            ctf_name = f"{ctf_name_input} {current_year}"

            try:
                # Format the start and end to unix time
                start_str = self.part1_data.get("start", "").strip()
                end_str = self.part1_data.get("end", "").strip()

                start_time_dt = datetime.datetime.strptime(
                    start_str, "%Y-%m-%d %H:%M"
                ).replace(tzinfo=datetime.timezone.utc)
                end_time_dt = datetime.datetime.strptime(
                    end_str, "%Y-%m-%d %H:%M"
                ).replace(tzinfo=datetime.timezone.utc)

            except ValueError:
                await inter.response.send_message(
                    "❌ Invalid date format. Please use YYYY-MM-DD HH:MM (UTC).",
                    ephemeral=True,
                )
                return
            if end_time_dt <= start_time_dt:
                await inter.response.send_message(
                    "❌ End time must be after start time.",
                    ephemeral=True,
                )
                return

            start_time = int(start_time_dt.timestamp())
            end_time = int(end_time_dt.timestamp())

            # Combine data from both modals
            part2_data = inter.text_values
            more_cats = inter.text_values.get("cats", "").strip()
            website = self.part1_data.get("website", "").strip()
            team_name = part2_data.get("teamname", "N/A").strip()
            password = part2_data.get("password", "").strip()
            discord_invite = part2_data.get("discord", "").strip()
            sheet_url = part2_data.get("sheet", "").strip()

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

            # Add credentials section if provided
            creds_value = f"**Team:** `{team_name}`"
            if password:
                creds_value += f"\n**Password:** ||`{password}`||"
            if discord_invite:
                creds_value += f"\n**Discord:** {discord_invite}"

            embed.add_field(name="🔒 Credentials", value=creds_value, inline=False)

            if website:
                embed.add_field(name="🌐 Website", value=website, inline=True)

            embed.set_footer(text=f"Registered by {inter.author.display_name}")

            try:
                await self.make_role(inter.guild, name=ctf_name)
                await self.make_ctf_channel(
                    guild=inter.guild,
                    channel_name=ctf_name.lower().replace(" ", "-"),
                    allowed_role=disnake.utils.get(inter.guild.roles, name=ctf_name),
                )
                await self.make_forum_channel(
                    guild=inter.guild,
                    channel_name=f"{ctf_name}-forum",
                    tags=[{"name": cat} for cat in all_categories],
                    # Pass CTF details to create the info thread
                    website=website,
                    start_time=start_time,
                    sheet_url=sheet_url,
                    end_time=end_time,
                    # ---
                    perms=(
                        lambda guild, ctf_role: {
                            guild.default_role: disnake.PermissionOverwrite(
                                view_channel=False
                            ),
                            ctf_role: disnake.PermissionOverwrite(view_channel=True),
                            **{
                                guild.get_role(
                                    player_role_id
                                ): disnake.PermissionOverwrite(view_channel=True)
                                for player_role_id in CTF_PLAYER_ROLES
                                if guild.get_role(player_role_id)
                            },
                        }
                    )(inter.guild, disnake.utils.get(inter.guild.roles, name=ctf_name)),
                )
            except Exception as e:
                print(f"Error creating role/channel/forum: {e}")

            # --- Check for announcement and send role button ---
            announcement_channel = inter.guild.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            role_button_sent = False
            if announcement_channel:
                one_day_ago = datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(days=1)
                found_announcement = False
                async for msg in announcement_channel.history(
                    after=one_day_ago, limit=100
                ):
                    if ctf_name_input.lower() in msg.content.lower():
                        found_announcement = True
                        break
                        await self.send_role_button(
                            announcement_channel, ctf_name, end_time
                        )
                        role_button_sent = True
                        break  # Stop searching

                if found_announcement:
                    view = GetRoleView(ctf_name=ctf_name, player_roles=CTF_PLAYER_ROLES)
                    button_embed = disnake.Embed(
                        title=f"Get the {ctf_name} Role!",
                        description=(
                            f"Click the button below to get the role for **{ctf_name}** and access the channels.\n"
                            "You must have a player role to do this."
                        ),
                        color=disnake.Color.blurple(),
                    )
                    if not role_button_sent:
                        print(
                            f"No recent announcement for '{ctf_name_input}'. Adding to pending list."
                        )
                        message = await announcement_channel.send(
                            embed=button_embed, view=view
                        )
                        role_button_sent = True
                        await Database.add_pending_announcement(
                            ctf_name_input.lower(), ctf_name, end_time_dt
                        )

                        # Store button info for auto-disabling
                        await Database.add_active_button(
                            ctf_name, message.id, announcement_channel.id, end_time_dt
                        )
                else:
                    print(
                        f"No recent announcement found for '{ctf_name_input}'. Skipping role button."
                    )
            else:
                print(
                    f"Could not find announcement channel with ID {ANNOUNCEMENT_CHANNEL_ID}"
                )

            response_message = "CTF registration processed successfully!"
            if not role_button_sent:
                response_message += "\n\n⚠️ **Note:** The 'Get Role' button was not sent because no corresponding announcement was found in the last 24 hours."
                response_message += "\n\n⏳ The 'Get Role' button will be sent automatically once an announcement for this CTF is detected."
            await inter.response.send_message(
                response_message, embed=embed, ephemeral=True
            )

            # --- Add CTF to database ---
            await Database.log_ctf(
                name=ctf_name,
                start_time=start_time_dt,
                end_time=end_time_dt,
                website=website,
                team_name=team_name,
                password=password,
                discord_invite=discord_invite,
                sheet_url=sheet_url,
                categories=all_categories,
                registered_by=inter.author.id,
            )
            # ---------------------------

            # Log the CTF registration (assuming Logger is properly set up)
            try:
                logger_instance = Logger(inter.bot)
                await logger_instance.log(
                    text=f"CTF registered: {ctf_name} by {inter.author} ({inter.author.id})",
                    color=disnake.Color.blue(),
                    type="CTF Registration",
                )
            except Exception as e:
                print(f"Logging error: {e}")

        except Exception as e:
            await inter.response.send_message(
                f"❌ An error occurred while processing your CTF registration: {str(e)}",
                ephemeral=True,
            )
            print(f"Modal callback error: {e}")

    async def send_role_button(
        self, channel: disnake.TextChannel, ctf_name: str, end_time: int
    ):
        """Sends the 'Get Role' button to the specified channel."""
        view = GetRoleView(ctf_name=ctf_name, player_roles=CTF_PLAYER_ROLES)
        embed = disnake.Embed(
            title=f"Get the {ctf_name} Role!",
            description=f"Click the button below to get the role for **{ctf_name}** and access the channels.\n"
            "You must have a player role to do this.",
            color=disnake.Color.blurple(),
        )
        message = await channel.send(embed=embed, view=view)

        # Store button info for auto-disabling
        end_time_dt = datetime.datetime.fromtimestamp(
            end_time, tz=datetime.timezone.utc
        )
        await Database.add_active_button(ctf_name, message.id, channel.id, end_time_dt)
        print(f"Sent role button for {ctf_name}")


class GetRoleView(disnake.ui.View):
    """A view with a button to claim a CTF role."""

    def __init__(self, ctf_name: str, player_roles: list, timeout=None):
        # Use a very long timeout; we will manage disabling it manually.
        super().__init__(timeout=timeout or 60 * 60 * 24 * 28)  # 28 days
        self.ctf_name = ctf_name
        self.player_roles = set(player_roles)
        self.add_item(
            disnake.ui.Button(
                label=f"Claim {ctf_name} Role",
                style=disnake.ButtonStyle.green,
                custom_id=f"get_ctf_role:{ctf_name}",
            )
        )


async def can_use_backup_command(ctx: commands.Context) -> bool:
    """Check if the user is an admin defined in the config."""
    return ctx.author.id in ADMIN_USER_IDS


def user_has_required_role(
    inter: disnake.MessageInteraction, required_roles: set
) -> bool:
    """Check if the interacting user has one of the required roles."""
    if not isinstance(inter.author, disnake.Member):
        return False
    user_role_ids = {role.id for role in inter.author.roles}
    return not user_role_ids.isdisjoint(required_roles)


@commands.command(name="sendrolebutton", hidden=True)
@commands.check(can_use_backup_command)
async def send_role_button_command(ctx: commands.Context, *, ctf_name: str):
    """
    Manually sends the 'Get Role' button for a CTF.
    Usage: !sendrolebutton <CTF Name with year>
    """
    if not ctf_name:
        await ctx.send("Please provide a CTF name.", delete_after=10)
        return

    role = disnake.utils.get(ctx.guild.roles, name=ctf_name)
    if not role:
        await ctx.send(f"Role `{ctf_name}` not found.", delete_after=10)
        return

    view = GetRoleView(ctf_name=ctf_name, player_roles=CTF_PLAYER_ROLES)
    embed = disnake.Embed(
        title=f"Get the {ctf_name} Role!",
        description=f"Click the button below to get the role for **{ctf_name}** and access the channels.\n"
        "You must have a player role to do this.",
        color=disnake.Color.blurple(),
    )
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()


class CTFSheet(commands.Cog):
    """Main cog for CTF management commands."""

    def __init__(self, bot):
        """Initialize the CTF cog."""
        self.bot = bot
        self.check_ended_ctfs.start()

    def cog_unload(self):
        """Stop the background task when the cog is unloaded."""
        self.check_ended_ctfs.cancel()

    @tasks.loop(minutes=10)
    async def check_ended_ctfs(self):
        """Periodically check for and disable buttons for ended CTFs."""
        now = datetime.datetime.now(datetime.timezone.utc)
        ended_ctfs = []

        active_buttons = await Database.get_active_buttons()

        for data in active_buttons:
            ctf_name = data["ctf_name"]
            if now >= data["end_time"]:
                try:
                    channel = self.bot.get_channel(
                        data["channel_id"]
                    ) or await self.bot.fetch_channel(data["channel_id"])
                    message = await channel.fetch_message(data["message_id"])

                    # Create a new view with a disabled button
                    disabled_view = disnake.ui.View()
                    disabled_view.add_item(
                        disnake.ui.Button(
                            label=f"{ctf_name} (Ended)",
                            style=disnake.ButtonStyle.grey,
                            disabled=True,
                        )
                    )

                    # Update the original message
                    await message.edit(view=disabled_view)
                    print(f"Disabled role button for ended CTF: {ctf_name}")
                    ended_ctfs.append(ctf_name)

                except disnake.NotFound:
                    print(
                        f"Message for CTF '{ctf_name}' not found. Removing from active list."
                    )
                    ended_ctfs.append(ctf_name)
                except Exception as e:
                    print(f"Error disabling button for CTF '{ctf_name}': {e}")

        # Clean up ended CTFs from the dictionary
        for ctf_name in ended_ctfs:
            await Database.remove_active_button(ctf_name)

    @check_ended_ctfs.before_loop
    async def before_check_ended_ctfs(self):
        await self.bot.wait_until_ready()

    @log(text="CTF registration started", color=0x00FF00)
    @commands.slash_command(
        name="register_ctf",
        description="Register a new CTF competition",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    @commands.cooldown(1, 30, commands.BucketType.user)  # 1 use per 30 seconds per user
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
                new_role_position = target_role.position
            else:
                new_role_position = 19

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
        guild: disnake.Guild,
        channel_name: str,
        tags: list[dict],
        perms: dict[disnake.Role | disnake.Member, disnake.PermissionOverwrite],
        website: str,
        start_time: int,
        sheet_url: str,
        end_time: int,
        require_tag: bool = True,
    ):
        """
        Create a forum channel with specified name, tags, and permissions.

        Args:
            guild: The Discord guild to create the channel in
            channel_name: Name of the forum channel
            tags: List of tag dictionaries with 'name' and optionally 'emoji' keys
            sheet_url: The URL for the Google Sheet.
            perms: Dictionary mapping role IDs/role objects to permission overwrites
            website: The URL for the CTF website.
            start_time: The UNIX timestamp for the CTF start time.
            end_time: The UNIX timestamp for the CTF end time.
            require_tag: Whether to require a tag when creating a post.
        """

        try:
            # Create the forum channel first
            forum_channel = await guild.create_forum_channel(
                name=channel_name,
                overwrites=perms,
                position=1,
                category=1382763557816500226,
            )

            # Set the require_tag flag
            flags = disnake.ChannelFlags(require_tag=require_tag)
            await forum_channel.edit(flags=flags)

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

            # Create the "Information" thread
            info_embed = disnake.Embed(
                title="CTF Information",
                color=disnake.Color.dark_teal(),
            )
            if website:
                info_embed.add_field(name="🌐 Website", value=website, inline=False)

            info_embed.add_field(
                name="⏰ Start Time", value=f"<t:{start_time}:F>", inline=True
            )
            info_embed.add_field(
                name="⏰ End Time", value=f"<t:{end_time}:F>", inline=True
            )
            sheet_value = sheet_url if sheet_url else "*Coming soon...*"
            info_embed.add_field(
                name="📊 Google Sheet", value=sheet_value, inline=False
            )

            # Create a view with a placeholder calendar button
            calendar_view = disnake.ui.View()
            calendar_view.add_item(
                disnake.ui.Button(
                    label="Add to Calendar",
                    style=disnake.ButtonStyle.secondary,
                    disabled=True,
                )
            )

            # Create, pin, and lock the thread
            thread = await forum_channel.create_thread(
                name="Information", embed=info_embed, view=calendar_view
            )
            await thread.edit(pinned=True, locked=True)

            print(
                f"Created forum channel: {forum_channel.name} with {len(forum_tags)} tags"
            )
            return forum_channel

        except disnake.HTTPException as e:
            print(f"Error creating forum channel: {e}")
            return None

    @commands.Cog.listener("on_button_click")
    @dynamic_cooldown()
    async def handle_get_role_button(self, inter: disnake.MessageInteraction):
        """Handle the 'Get Role' button click."""
        custom_id = inter.component.custom_id
        if not custom_id or not custom_id.startswith("get_ctf_role:"):
            return

        ctf_name = custom_id.split(":", 1)[1]

        if not user_has_required_role(inter, set(CTF_PLAYER_ROLES)):
            await inter.response.send_message(
                "❌ You don't have the required role to claim this CTF role.",
                ephemeral=True,
            )
            # Reset cooldown if check fails
            inter.application_command.reset_cooldown(inter)
            return

        role_to_assign = disnake.utils.get(inter.guild.roles, name=ctf_name)
        if not role_to_assign:
            await inter.response.send_message(
                f"❌ The role `{ctf_name}` could not be found.", ephemeral=True
            )
            return

        if role_to_assign in inter.author.roles:
            await inter.response.send_message(
                "✅ You already have this role.", ephemeral=True
            )
            return

        try:
            await inter.author.add_roles(
                role_to_assign, reason=f"Claimed via button for {ctf_name}"
            )
            await inter.response.send_message(
                f"✅ You have been given the **{ctf_name}** role!", ephemeral=True
            )
        except disnake.Forbidden:
            await inter.response.send_message(
                "❌ I don't have permission to assign roles.", ephemeral=True
            )
        except Exception as e:
            await inter.response.send_message(
                f"❌ An error occurred: {e}", ephemeral=True
            )

    @commands.Cog.listener("on_message")
    async def on_announcement_message(self, message: disnake.Message):
        """Listen for new messages in the announcement channel."""
        # Ignore bots, DMs, and messages not in the announcement channel
        if (
            message.author.bot
            or not message.guild
            or message.channel.id != ANNOUNCEMENT_CHANNEL_ID
        ):
            return

        pending = await Database.get_pending_announcements()

        # Check if the message content matches any pending CTFs
        for item in pending:
            ctf_name_input = item["ctf_name_input"]
            data = item
            if ctf_name_input in message.content.lower():
                print(f"Announcement detected for '{ctf_name_input}'. Sending button.")
                await CTFModalPart2.send_role_button(
                    self,
                    message.channel,
                    data["ctf_name"],
                    int(data["end_time"].timestamp()),
                )
                await Database.remove_pending_announcement(ctf_name_input)


def setup(bot):
    bot.add_cog(CTFSheet(bot))
