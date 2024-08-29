"""This module contains some useful callbacks for menus."""
from typing import Callable, Any

from nextcord import Interaction


async def value_callback(key: str, value: Any) -> Callable:
    """Creates a callback that sets a value in the view."""

    async def callback(self, _: Interaction) -> None:
        self.view.values[key] = value

    return callback


async def value_stop_callback(key: str, value: Any) -> Callable:
    """Creates a callback that sets a value in the view and stops the view."""

    async def callback(self, _: Interaction) -> None:
        self.view.values[key] = value
        self.view.stop()

    return callback
