"""Cog to hold commands to set up the registration part of the bot per server."""

import nextcord
from nextcord.ext import commands
from nextcord.ui import RoleSelect

from constants import BOT_COLOR
from registration import RegistrationSettings
from menus import BotMenu
from menus.callbacks import action_callback
from menus.templates import send_channel_prompt


async def send_role_selects(
    interaction: nextcord.Interaction, menu: BotMenu, roles: list[str]
) -> dict[str, int | None]:
    """Sends role select menus until all roles have been selected."""
    role_ids: dict[str, int | None] = {}
    while len(roles) > 0:
        menu.clear_entry_fields()
        await menu.edit(interaction)
        num_roles: int = min(
            len(roles), 4
        )  # Discord only supports up to 4 role selects in one view
        for role in roles[:num_roles]:
            role_select: RoleSelect = RoleSelect(
                placeholder=f"{role.capitalize()} Role", max_values=1, custom_id=role
            )
            menu.add_item(role_select)
        await menu.edit(interaction)
        if (
            not await menu.wait_for_action(interaction.client)
            or menu.action == "cancel"
        ):
            raise TimeoutError

        for menu_child in menu.children:  # Don't include the continue/cancel buttons
            if isinstance(menu_child, RoleSelect):
                role_ids[menu_child.custom_id] = (
                    menu_child.values.roles[0].id
                    if len(menu_child.values.roles) > 0
                    else None
                )
                roles.remove(menu_child.custom_id)

    menu.clear_entry_fields()
    await interaction.edit_original_message(view=None)  # Refresh role entries
    return role_ids


async def send_role_select(
    interaction: nextcord.Interaction, menu: BotMenu, role: str
) -> int | None:
    """Sends a single role select menu."""
    menu.clear_entry_fields()
    role_select: RoleSelect = RoleSelect(
        placeholder=f"{role.capitalize()} Role", max_values=1, custom_id=role
    )
    menu.add_item(role_select)
    await menu.edit(interaction)
    if not await menu.wait_for_action(interaction.client) or menu.action == "cancel":
        raise TimeoutError

    menu.clear_entry_fields()
    await interaction.edit_original_message(view=None)  # Refresh role entries
    return role_select.values.roles[0].id if len(role_select.values.roles) > 0 else None


def setup_reg_embed(embed: nextcord.Embed, settings: RegistrationSettings) -> None:
    """Add fields showing all the registration settings to the embed."""
    embed.clear_fields()
    embed.add_field(
        name="Settings",
        value=f"Enabled: {settings.enabled}\nGamemode: {settings.gamemode}\nMode: {settings.mode}",
        inline=True,
    )
    embed.add_field(
        name="General Roles",
        value=f"Registered: <@&{settings.roles.registered}>\nBypass: <@&{settings.roles.bypass}>\nBan: <@&{settings.roles.ban}>",
        inline=True,
    )
    embed.add_field(name="Channels", value=str(settings.channels), inline=True)
    match settings.gamemode:
        case "sixes" | "combined":
            embed.add_field(name="Roles", value=str(settings.roles.sixes), inline=False)
        case "highlander":
            embed.add_field(
                name="Roles", value=str(settings.roles.highlander), inline=False
            )
        case "both":
            embed.add_field(
                name="Sixes Roles", value=str(settings.roles.sixes), inline=False
            )
            embed.add_field(
                name="Highlander Roles",
                value=str(settings.roles.highlander),
                inline=True,
            )


async def check_channel_perms(guild: nextcord.Guild, channel_id: int) -> bool:
    """Check if the bot has permission to access and send messages in the channel."""
    channel: nextcord.abc.GuildChannel | None = guild.get_channel(channel_id)
    if channel is None:
        return False
    permissions = channel.permissions_for(guild.me)
    return permissions.read_messages and permissions.send_messages


class RegistrationSetupCog(commands.Cog):
    """Cog storing the registration setup command."""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @nextcord.slash_command(
        name="registration",
        description="Setup pugBot.tf registration for this server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def setup_registration(self, interaction: nextcord.Interaction):
        """Setup pugBot.tf registration for this server."""
        settings = RegistrationSettings()
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command must be run in a server.", ephemeral=True
            )
            return
        if interaction.user is None:
            await interaction.response.send_message(
                "This command must be run by a user.", ephemeral=True
            )
            return

        await settings.load_data(interaction.guild.id)
        setup_embed = nextcord.Embed(
            title="Registration Setup",
            color=BOT_COLOR,
            description="Registration allows for you to link new members of the server to https://pugBot.tf/register, which can give them division roles based on their RGL experience.\n\nYou can have it go off either their current or highest division played, in either 6s or Highlander.\n\nYou will need to create your own division roles. You will match the divisions with the role you would like to be assigned in the setup menu.",
        )
        setup_reg_embed(setup_embed, settings)

        menu: BotMenu = BotMenu(embed=setup_embed, user_id=interaction.user.id)
        menu.add_button(
            "Enable",
            await action_callback("enable", interaction.user.id),
            nextcord.ButtonStyle.green,
        )
        menu.add_button(
            "Disable",
            await action_callback("disable", interaction.user.id),
            nextcord.ButtonStyle.red,
        )
        menu.add_button(
            "Cancel",
            await action_callback("cancel", interaction.user.id),
            nextcord.ButtonStyle.gray,
        )
        await menu.send(interaction)
        if not await menu.wait_for_action(interaction.client) or menu.action is None:
            await interaction.delete_original_message()
            return
        action: str = menu.action
        match action:
            case "disable":
                settings.enabled = False
                await settings.upload_data(interaction.guild.id)
                setup_embed.description = "Registration has been disabled."
                menu.embed = setup_embed
                await menu.edit(interaction)
                await interaction.delete_original_message(delay=5)
                return
            case "cancel":
                await interaction.delete_original_message()
                return

        settings.enabled = True

        # Registration is being enabled, start reg settings setup
        # Start with prompting for gamemode to know how many div roles to prompt for
        menu.clear_items()
        setup_embed.clear_fields()
        setup_embed.description = "Please select the gamemode you would like to use for division role assignment.\n- Sixes: Use Sixes RGL history\n- Highlander: Use Highlander RGL history\n- Both: Set up roles for both Sixes and Highlander\n- Combined: Use the highest of the two modes"
        await menu.add_action_buttons(
            ["Sixes", "Highlander", "Both", "Combined"], interaction.user.id
        )
        await menu.edit(interaction)
        if (
            not await menu.wait_for_action(interaction.client)
            or menu.action == "cancel"
        ):
            await interaction.delete_original_message()
            return
        settings.gamemode = menu.action.lower()

        # Mode selection (highest or current division)
        menu.clear_items()
        setup_embed.description = "Please select the mode you would like to use for role assignment.\n\nYou can either go by the highest division played, or the current division played."
        await menu.add_action_buttons(["Highest", "Current"], interaction.user.id)
        await menu.edit(interaction)
        if (
            not await menu.wait_for_action(interaction.client)
            or menu.action == "cancel"
        ):
            await interaction.delete_original_message()
            return
        settings.mode = menu.action.lower()

        # Start assigning the division roles
        menu.clear_items()
        await menu.add_continue_buttons()
        setup_embed.description = "Please select the roles you would like to be assigned to each division. You can select one role for multiple divisions. You can also put no role if you do not want players with that division to be assigned. Noexp stands for no experience (no team history in RGL).\n\n**Note: Due to client-side discord limitations, you may need to SEARCH for the role in the select menu.**"
        if settings.gamemode in (
            "sixes",
            "both",
            "combined",
        ):  # These modes assign roles to the sixes divisions
            # Sixes roles
            if settings.gamemode == "combined":
                setup_embed.title = "Combined Division Roles"
            else:
                setup_embed.title = "Sixes Division Roles"
            try:
                role_ids: dict[str, int | None] = await send_role_selects(
                    interaction,
                    menu,
                    [
                        "noexp",
                        "newcomer",
                        "amateur",
                        "intermediate",
                        "main",
                        "advanced",
                        "invite",
                    ],
                )
            except TimeoutError:
                await interaction.delete_original_message(delay=1)
                return
            for role, role_id in role_ids.items():
                setattr(settings.roles.sixes, role, role_id)
        if settings.gamemode in (
            "highlander",
            "both",
        ):  # These modes assign roles to the highlander divisions
            setup_embed.title = "Highlander Division Roles"
            try:
                role_ids = await send_role_selects(
                    interaction,
                    menu,
                    [
                        "noexp",
                        "newcomer",
                        "amateur",
                        "intermediate",
                        "main",
                        "advanced",
                        "invite",
                    ],
                )
            except TimeoutError:
                await interaction.delete_original_message(delay=1)
                return
            for role, role_id in role_ids.items():
                setattr(settings.roles.highlander, role, role_id)

        # Registered role select
        setup_embed.title = "Registration Setup"
        setup_embed.description = "Please select the role you would like to be assigned to registered players. You can continue without selecting a role if you do not want a role to be assigned."
        try:
            settings.roles.registered = await send_role_select(
                interaction, menu, "registered"
            )
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return

        # Bypass select
        setup_embed.description = "Select a role that will block any role updates for anyone who has it if you would like to. This is useful for if you need to manually assign roles to someone, or if you want to block someone from getting roles."
        try:
            settings.roles.bypass = await send_role_select(interaction, menu, "bypass")
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return

        # Ban select
        setup_embed.description = "Select a role to be given to players who are RGL banned. You do not have to select a role if you do not want to assign a role to banned players."
        try:
            settings.roles.ban = await send_role_select(interaction, menu, "Ban")
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return

        # Channel select
        setup_embed.description = "Lastly, please select the channels you would like to be used for new registrations and logging of role changes.\nYou can use the same channel for both, if desired.\n\nJust like for selecting roles, you may need to search for it."
        try:
            channels: list[nextcord.TextChannel | None] = await send_channel_prompt(
                menu,
                interaction,
                ["New Registration Channel", "Update Log Channel"],
                False,
                [nextcord.ChannelType.text],
            )
        except TimeoutError:
            await interaction.delete_original_message()
            return
        settings.channels.registration = (
            channels[0].id if channels[0] is not None else None
        )
        settings.channels.logs = channels[1].id if channels[1] is not None else None

        # Check if bot can access and type in the channels
        if settings.channels.registration and not await check_channel_perms(
            interaction.guild, settings.channels.registration
        ):
            await interaction.edit_original_message(
                content=f"The bot does not have permission to access and type in the registration channel (<#{settings.channels.registration}>). Please check the permissions and try again.",
                view=None,
            )
            return
        if settings.channels.logs and not await check_channel_perms(
            interaction.guild, settings.channels.logs
        ):
            await interaction.edit_original_message(
                content=f"The bot does not have permission to access and type in the logs channel (<#{settings.channels.logs}>). Please check the permissions and try again.",
                view=None,
            )
            return

        setup_embed.description = "Registration setup complete! You can now link new members of the server to https://pugbot.tf/register, and roles will be assigned from the bot.\n\nUse /updateall to update all current members of the server, or wait for the bots daily update.\n\nMake sure the bot has permission to assign all roles and access the channels you selected!"
        menu.clear_items()
        setup_reg_embed(setup_embed, settings)
        await settings.upload_data(interaction.guild.id)
        await interaction.edit_original_message(embed=setup_embed, view=None)
