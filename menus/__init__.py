"""Adds classes and functions to easily make menus in Discord views."""
from typing import Callable, Optional

import nextcord
from nextcord.ui import View


class BotMenu(View):
    """Represents a menu for the bot to use.

    Parameters
    ----------
    View : nextcord.ui.View
        The base nextcord View.
    """

    def __init__(self, embed: Optional[nextcord.Embed]) -> None:
        View.__init__(self)
        self.embed = embed
        self.values: dict = {}

    async def add_button(
        self, label: str, callback: Callable, style: nextcord.ButtonStyle
    ) -> None:
        """Adds a button to the menu.

        Parameters
        ----------
        label : str
            The text to display on the button.
        style : nextcord.ButtonStyle
            The style of the button.
        custom_id : str
            The custom ID of the button.
        """

        class MenuButton(nextcord.ui.Button):
            """Represents a button in the menu."""

            def __init__(self):
                nextcord.ui.Button.__init__(self, label=label, style=style)

            async def callback(self, interaction: nextcord.Interaction):
                await callback(self, interaction)

        View.add_item(self, MenuButton())

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
