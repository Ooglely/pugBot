"""This module contains some useful callbacks for menus."""
from typing import Callable, Any

from nextcord import Interaction


async def value_callback(key: str, value: Any, author: int) -> Callable:
    """Creates a callback that sets a value in the view."""

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user is not None and interaction.user.id == author:
            self.view.values[key] = value

    return callback


async def action_callback(value: Any, author: int) -> Callable:
    """Creates a callback that sets the action in the menu."""

    async def callback(self, interaction: Interaction) -> None:
        if interaction.user is not None and interaction.user.id == author:
            self.view.action = value

    return callback
