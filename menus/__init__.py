"""Adds classes and functions to easily make menus in Discord views."""
import asyncio
from typing import Callable, Optional

import nextcord
from nextcord.ui import View

from menus.callbacks import action_stop_callback


class BotMenu(View):
    """Represents a menu for the bot to use.

    Parameters
    ----------
    View : nextcord.ui.View
        The base nextcord View.
    """

    def __init__(self, embed: Optional[nextcord.Embed] = None) -> None:
        View.__init__(self)
        self.embed = embed
        self.values: dict = {}
        self.action: str | None = None

    def add_button(
        self, label: str, callback: Callable, style: nextcord.ButtonStyle
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
                nextcord.ui.Button.__init__(self, label=label, style=style)

            async def callback(self, interaction: nextcord.Interaction):
                await callback(self, interaction)

        View.add_item(self, MenuButton())

    async def add_continue_buttons(self, author: int) -> None:
        """Adds continue and cancel buttons to the menu."""
        self.add_button("Continue", await action_stop_callback("continue", author), nextcord.ButtonStyle.green)
        self.add_button("Cancel", await action_stop_callback("cancel", author), nextcord.ButtonStyle.red)

    async def send(self, interaction: nextcord.Interaction) -> None:
        """Sends the menu to the interaction."""
        if self.embed:
            await interaction.response.send_message(embed=self.embed, view=self)
        else:
            await interaction.send(view=self)

    async def edit(self, interaction: nextcord.Interaction) -> None:
        """Edits the menu in the interaction."""
        if self.embed:
            await interaction.response.edit_message(embed=self.embed, view=self)
        else:
            await interaction.response.edit_message(view=self)

    async def delete_after(self, interaction: nextcord.Interaction, delay: int) -> None:
        """Deletes the menu after a delay."""
        await asyncio.sleep(delay)
        await interaction.delete_original_message()
        
    def clear_fields(self) -> None:
        """Clears all children of the view that are not buttons."""
        for child in self.children:
            if not isinstance(child, nextcord.ui.Button):
                self.remove_item(child)
