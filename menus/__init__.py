"""Adds classes and functions to easily make menus in Discord views."""
import asyncio
from typing import Callable, Optional

import nextcord
from nextcord.ui import View, Item
from nextcord.enums import ComponentType

from menus.callbacks import action_callback


class BotMenu(View):
    """Represents a menu for the bot to use.

    Parameters
    ----------
    View : nextcord.ui.View
        The base nextcord View.
    """

    def __init__(self, user_id: int, embed: Optional[nextcord.Embed] = None) -> None:
        View.__init__(self)
        self.embed = embed
        self.values: dict = {}
        self.action: str | None = None
        self.user: int = user_id
        self.message_id: int | None = None

    def add_button(
        self,
        label: str,
        callback: Callable,
        style: nextcord.ButtonStyle = nextcord.ButtonStyle.grey,
        row: int | None = None,
    ) -> None:
        """Adds a button to the menu.

        Parameters
        ----------
        label : str
            The text to display on the button.
        callback : Callable
            A callback function for after the button is pressed.
        style : nextcord.ButtonStyle
            The style of the button.
        """

        class MenuButton(nextcord.ui.Button):
            """Represents a button in the menu."""

            def __init__(self):
                nextcord.ui.Button.__init__(self, label=label, style=style, row=row)

            async def callback(self, interaction: nextcord.Interaction):
                await callback(self, interaction)

        View.add_item(self, MenuButton())

    async def add_continue_buttons(self) -> None:
        """Adds continue and cancel buttons to the menu."""
        self.add_button(
            "Continue",
            await action_callback("continue", self.user),
            nextcord.ButtonStyle.green,
        )
        self.add_button(
            "Cancel",
            await action_callback("cancel", self.user),
            nextcord.ButtonStyle.red,
        )

    async def add_action_buttons(self, items: list[str], author: int) -> None:
        """Adds buttons for each item in the list."""
        for item in items:
            self.add_button(
                item.capitalize(),
                await action_callback(item, author),
                nextcord.ButtonStyle.grey,
            )

    def get_child(self, custom_id: str) -> nextcord.ui.Item | None:
        """Gets a child button by its custom id."""
        for child in self.children:
            if hasattr(child, "custom_id") and child.custom_id == custom_id:
                return child
        return None

    async def send(self, interaction: nextcord.Interaction) -> None:
        """Sends the menu to the interaction."""
        self.action = None
        if self.embed:
            await interaction.send(embed=self.embed, view=self)
        else:
            await interaction.send(view=self)
        self.message_id = (await interaction.original_message()).id

    async def wait_for_action(self, client: nextcord.Client) -> bool:
        """
        Waits for an action to be associated with the menu.
        Returns True if an action was received, False if it timed out.
        """

        def button_check(interaction: nextcord.Interaction) -> bool:
            if not interaction.message or interaction.message.id != self.message_id:
                # This is to prevent interactions with other menus activating the check
                return False
            if interaction.user is None:  # No user associated with the interaction?
                return False
            if (
                interaction.type is not nextcord.InteractionType.component
                or interaction.data is None
            ):  # Interaction is not a button press
                return False
            if (
                interaction.user.id == self.user
                and interaction.data.get("component_type") == 2
            ):  # Button
                return True
            return False

        try:
            await client.wait_for("interaction", check=button_check, timeout=180)
            return True
        except asyncio.TimeoutError:
            return False

    async def edit(self, interaction: nextcord.Interaction) -> None:
        """Edits the menu in the interaction."""
        self.action = None
        if self.embed:
            msg = await interaction.edit_original_message(embed=self.embed, view=self)
        else:
            msg = await interaction.edit_original_message(view=self)
        self.message_id = msg.id

    def clear_entry_fields(self) -> None:
        """Clears all children of the view that are not buttons."""
        items_to_remove: list[Item] = []
        for child in self.children:  # Skip buttons
            if child.type == ComponentType.role_select:
                items_to_remove.append(child)

        for item in items_to_remove:
            self.remove_item(item)
