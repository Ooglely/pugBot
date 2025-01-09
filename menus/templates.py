"""Functions to build predefined  for use around the bot."""
from nextcord import ButtonStyle, Interaction
from nextcord.abc import GuildChannel
from nextcord.enums import ChannelType
from nextcord.ui import ChannelSelect
from nextcord.utils import MISSING

from menus import BotMenu
from menus.callbacks import action_callback


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
