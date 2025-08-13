"""Functions to build predefined  for use around the bot."""
from nextcord import ButtonStyle, Interaction, Embed
from nextcord.abc import GuildChannel
from nextcord.enums import ChannelType
from nextcord.ui import ChannelSelect
from nextcord.utils import MISSING

from menus import BotMenu
from menus.callbacks import action_callback
from registration import RegistrationSettings
from pug import Teams

# pylint: disable=too-many-positional-arguments


async def send_boolean_menu(menu: BotMenu, interaction: Interaction) -> bool:
    """Creates and sends a boolean menu.

    Parameters
    ----------
    menu : BotMenu
        The menu to send.
    interaction : Interaction
        The interaction to send the menu to.

    Returns
    -------
    bool
        The result of the menu.

    Raises
    ------
    TimeoutError
        If the menu times out.
    """
    menu.clear_items()
    menu.add_button(
        "Yes", await action_callback("enable", menu.user), ButtonStyle.green
    )
    menu.add_button("No", await action_callback("disable", menu.user), ButtonStyle.red)
    if interaction.response.is_done():
        await menu.edit(interaction)
    else:
        await menu.send(interaction)
    if not await menu.wait_for_action(interaction.client):
        raise TimeoutError
    return menu.action == "enable"


async def send_channel_prompt(
    menu: BotMenu,
    interaction: Interaction,
    channels: list[str],
    required: bool,
    allowed_types: list[ChannelType] = MISSING,
) -> list[GuildChannel | None]:
    """Prompts the user to select channels.

    Parameters
    ----------
    menu : BotMenu
        The menu to send.
    interaction : Interaction
        The interaction to send the menu to.
    channels : list[str]
        The channels to prompt the user to select from.
    required : bool
        Whether the user must select a channel for each entry.
    allowed_types : list[ChannelType], optional
        The types of channels that can be selected in the selects, by default all types are allowed

    Returns
    -------
    list[int | None]
        The selected channels.

    Raises
    ------
    TimeoutError
        If the menu times out.
    ValueError
        If required is True and no channel is selected for a entry.
    """
    channel_selects: list[
        ChannelSelect
    ] = []  # We'll go through this later to get the values
    menu.clear_items()
    if interaction.response.is_done():
        await menu.edit(interaction)
    else:
        await menu.send(interaction)
    while (
        len(channels) > 0
    ):  # since max prompt rows is 4, we may need to send this multiple times
        menu.clear_entry_fields()
        await menu.edit(interaction)  # Refresh discord cache of the entry fields
        num_channels: int = min(len(channels), 4)
        for channel in channels[:num_channels]:
            select: ChannelSelect = ChannelSelect(
                placeholder=channel, max_values=1, channel_types=allowed_types
            )
            channel_selects.append(select)
            menu.add_item(select)
        await menu.add_continue_buttons()
        await menu.edit(interaction)
        if (
            not await menu.wait_for_action(interaction.client)
            or menu.action == "cancel"
        ):
            raise TimeoutError
        channels = channels[num_channels:]
    # Now we need to get the values of the channel selects
    selected_channels: list[GuildChannel | None] = []
    for channel_select in channel_selects:
        if len(channel_select.values) == 0:
            if required:
                raise ValueError("No channel selected.")
            selected_channels.append(None)
        else:
            selected_channels.append(channel_select.values[0])

    return selected_channels


class TeamGenMenu(BotMenu):
    """A menu for generating teams."""

    def __init__(
        self,
        user: int,
        embed: Embed,
        reg_settings: RegistrationSettings,
        elo_enabled: bool,
        role_enabled: bool,
    ):
        embed.clear_fields()
        super().__init__(user, embed)
        self.reg_settings = reg_settings
        self.elo_enabled = elo_enabled
        self.role_enabled = role_enabled

    async def add_gen_buttons(self) -> None:
        """Adds move and reroll buttons for the different modes depending on the servers settings."""
        if self.elo_enabled:
            self.add_button(
                "🔁 ELO", await action_callback("elo", self.user), ButtonStyle.grey, 0
            )
        if self.reg_settings.enabled:
            match self.reg_settings.gamemode:
                case "sixes" | "highlander" | "combined":
                    self.add_button(
                        f"🔁 {self.reg_settings.gamemode.capitalize()} Divisions",
                        await action_callback(self.reg_settings.gamemode, self.user),
                        ButtonStyle.grey,
                        0,
                    )
                case "both":
                    self.add_button(
                        "🔁 6s",
                        await action_callback("sixes", self.user),
                        ButtonStyle.grey,
                        0,
                    )
                    self.add_button(
                        "🔁 HL",
                        await action_callback("highlander", self.user),
                        ButtonStyle.grey,
                        0,
                    )
        if self.role_enabled:
            self.add_button(
                "🔁 Roles",
                await action_callback("roles", self.user),
                ButtonStyle.grey,
                0,
            )
        self.add_button(
            "🔁 Random", await action_callback("random", self.user), ButtonStyle.grey, 0
        )
        self.add_button(
            "✅ Move", await action_callback("move", self.user), ButtonStyle.green, 1
        )
        self.add_button(
            "🗑️ Cancel", await action_callback("cancel", self.user), ButtonStyle.red, 1
        )

    async def update_teams(self, teams: Teams) -> None:
        """Update the embed with the given team list."""
        if not self.embed:
            return
        self.embed.clear_fields()
        red_team_string: str = ""
        blu_team_string: str = ""
        red_team_score: int = 0
        blu_team_score: int = 0
        team_count: int = min(len(teams["red"]), len(teams["blu"]))

        if team_count == 0:
            print("Teams: ", teams["red"], teams["blu"])
            raise ValueError("No players in one of the teams. Cannot generate teams.")

        if self.action in ("elo", "roles"):
            for player in teams["red"]:
                red_team_score += player.elo
                if player.icon:
                    red_team_string += (
                        f"[**{player.elo}**] {player.icon} <@{player.discord}>\n"
                    )
                else:
                    red_team_string += f"[**{player.elo}**] <@{player.discord}>\n"
            for player in teams["blu"]:
                blu_team_score += player.elo
                if player.icon:
                    blu_team_string += (
                        f"[**{player.elo}**] {player.icon} <@{player.discord}>\n"
                    )
                else:
                    blu_team_string += f"[**{player.elo}**] <@{player.discord}>\n"
        elif self.action in ("sixes", "highlander", "combined"):
            teams["red"].sort(
                key=lambda x: x.get_division(self.action, self.reg_settings.mode)  # type: ignore
            )
            teams["blu"].sort(
                key=lambda x: x.get_division(self.action, self.reg_settings.mode)  # type: ignore
            )
            for player in teams["red"]:
                player_division: int = player.get_division(
                    self.action, self.reg_settings.mode
                )
                if player_division != -1:
                    red_team_score += player_division
                player_level: str = (
                    str(player_division) if player_division != -1 else "?"
                )
                red_team_string += f"[**{player_level}**] <@{player.discord}>\n"
            for player in teams["blu"]:
                player_division = player.get_division(
                    self.action, self.reg_settings.mode
                )
                if player_division != -1:
                    blu_team_score += player_division
                player_level = str(player_division) if player_division != -1 else "?"
                blu_team_string += f"[**{player_level}**] <@{player.discord}>\n"
        elif self.action == "random":
            for player in teams["red"]:
                red_team_string += f"[**?**] <@{player.discord}>\n"
            for player in teams["blu"]:
                blu_team_string += f"[**?**] <@{player.discord}>\n"
        else:
            raise ValueError(f"Invalid view action: {self.action}")

        if self.action == "random":
            self.embed.add_field(name="🔵 Blu Team", value=blu_team_string)
            self.embed.add_field(name="🔴 Red Team", value=red_team_string)
        else:
            self.embed.add_field(
                name=f"🔵 Blu Team\nScore: {(blu_team_score / team_count):.2f}",
                value=blu_team_string,
            )
            self.embed.add_field(
                name=f"🔴 Red Team\nScore: {(red_team_score / team_count):.2f}",
                value=red_team_string,
            )

        self.embed.description = f"Current generation mode: {self.action.capitalize()}"
