"""Holds classes for pug commands/setup"""
from typing import Union, List, Dict
import time

import nextcord

from database import get_player_from_discord, get_player_from_steam, BotCollection

default_category = {
    "name": "",
    "add_up": None,
    "red_team": None,
    "blu_team": None,
    "next_pug": None,
    "first_to": {
        "enabled": False,
        "num": 0,
    },
}

config_db = BotCollection("guilds", "config")
category_db = BotCollection("guilds", "categories")


class PugPlayer:
    """Represents a player in the pug."""

    def __init__(
        self, steam: Union[int, None] = None, discord: Union[int, None] = None
    ):
        try:
            if steam is not None:
                player_data = get_player_from_steam(steam)
            elif discord is not None:
                player_data = get_player_from_discord(discord)
            else:
                raise KeyError
            registered = True
        except LookupError:
            player_data = {
                "steam": steam,
                "discord": discord,
                "divison": {
                    "sixes": {"highest": -1, "current": -1},
                    "hl": {"highest": -1, "current": -1},
                },
            }
            registered = False
        if "divison" not in player_data:
            player_data["divison"] = {
                "sixes": {"highest": -1, "current": -1},
                "hl": {"highest": -1, "current": -1},
            }
        self.steam: int | None = (
            int(player_data["steam"]) if player_data["steam"] else None
        )
        self.discord: int | None = (
            int(player_data["discord"]) if player_data["discord"] else None
        )
        self.division: Dict[str, Dict[str, int]] = player_data["divison"]
        self.registered: bool = registered
        self.elo: int = 0


class PugCategory:
    """Represents a pug category, settings and channel for a section of pugs"""

    def __init__(
        self, name: str, category=default_category
    ):  # pylint: disable=dangerous-default-value
        self.name: str = name
        self.add_up: int = category["add_up"]
        self.red_team: int = category["red_team"]
        self.blu_team: int = category["blu_team"]
        self.next_pug: int = category["next_pug"]
        self.first_to = category["first_to"]

    def __dict__(self):
        return {
            "name": self.name,
            "add_up": self.add_up,
            "red_team": self.red_team,
            "blu_team": self.blu_team,
            "next_pug": self.next_pug,
            "first_to": self.first_to,
        }

    async def add_to_db(self, guild: int):
        """Adds the category to the database."""
        print(self.__dict__())  # pylint: disable=not-callable
        await category_db.update_item(
            {"_id": guild},
            {
                "$set": {
                    f"categories.{self.name}": self.__dict__()  # pylint: disable=not-callable
                }
            },
        )

    async def remove_from_db(self, guild: int):
        """Removes the category from the database."""
        await category_db.update_item(
            {"_id": guild},
            {"$unset": {f"categories.{self.name}": ""}},
        )

    async def get_last_players(self, guild: int) -> tuple[List[PugPlayer], int]:
        """Gets the last players from the database."""
        try:
            result = await category_db.find_item({"_id": guild})
        except LookupError as exc:
            raise exc
        print(result["categories"])
        if (
            self.name not in result["categories"]
            or "players" not in result["categories"][self.name]
        ):
            raise LookupError
        players: List[PugPlayer] = []
        for player in result["categories"][self.name]["players"]:
            print(player)
            players.append(PugPlayer(discord=player["discord"]))
        timestamp: int
        try:
            timestamp = result["categories"][self.name]["timestamp"]
        except KeyError:
            timestamp = round(time.time()) - 7200
        return players, timestamp

    async def update_last_players(self, guild: int, players: List[PugPlayer]) -> None:
        """Updates the last players in the database."""
        last_players = []
        for player in players:
            last_players.append(player.__dict__)
        await category_db.update_item(
            {"_id": guild},
            {
                "$set": {
                    f"categories.{self.name}.players": last_players,
                    f"categories.{self.name}.timestamp": round(time.time()),
                }
            },
        )


class PugChannelSelect(nextcord.ui.View):
    """View to select pug channels."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.add_up = None
        self.red_team = None
        self.blu_team = None

    @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
    async def finish(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Continues setup"""
        self.action = "continue"
        self.stop()

    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red)
    async def cancel(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Cancels setup"""
        self.action = "cancel"
        self.stop()

    @nextcord.ui.channel_select(placeholder="Add up/selecting channel")
    async def add_up(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select the channel that users will add up in.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.add_up = channel.values[0].id

    @nextcord.ui.channel_select(placeholder="RED Team channel")
    async def red_team(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel for the RED team to join.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.red_team = channel.values[0].id

    @nextcord.ui.channel_select(placeholder="BLU Team channel")
    async def blu_team(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel for the BLU team to join.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.blu_team = channel.values[0].id


class FirstToSelect(nextcord.ui.View):
    """A view to select the settings for first to x pugs."""

    def __init__(self):
        super().__init__()
        self.selection: bool = False
        self.num: int = 0

    @nextcord.ui.button(label="Ultiduo (4)", style=nextcord.ButtonStyle.grey)
    async def ultiduo(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects ultiduo as the gamemode"""
        self.selection = True
        self.num = 4
        self.stop()

    @nextcord.ui.button(label="Ultitrio (6)", style=nextcord.ButtonStyle.grey)
    async def ultitrio(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects ultitrio as the gamemode"""
        self.selection = True
        self.num = 6
        self.stop()

    @nextcord.ui.button(label="Passtime (8)", style=nextcord.ButtonStyle.grey)
    async def passtime(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects ultitrio as the gamemode"""
        self.selection = True
        self.num = 8
        self.stop()

    @nextcord.ui.button(label="6s (12)", style=nextcord.ButtonStyle.grey)
    async def sixes(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects 6s as the gamemode"""
        self.selection = True
        self.num = 12
        self.stop()

    @nextcord.ui.button(label="Highlander (18)", style=nextcord.ButtonStyle.grey)
    async def highlander(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects HL as the gamemode"""
        self.selection = True
        self.num = 18
        self.stop()

    @nextcord.ui.button(label="None", style=nextcord.ButtonStyle.red)
    async def none(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Disables first to x pugs"""
        self.selection = False
        self.num = 0
        self.stop()


class FirstToChannelSelect(nextcord.ui.View):
    """View to select first to x channel."""

    def __init__(self):
        super().__init__()
        self.first_to: int = 0

    @nextcord.ui.channel_select(custom_id="first_to", placeholder="In Next Pug channel")
    async def first_to_select(
        self, channel: nextcord.ui.ChannelSelect, _interaction: nextcord.Interaction
    ):
        """Select a channel to send new registrations to.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        self.first_to = channel.values[0].id
        self.stop()


class CategorySelect(nextcord.ui.View):
    """View to show all categories."""

    def __init__(self):
        super().__init__()
        self.name: str = ""

    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red, row=4)
    async def cancel(
        self, _button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        """Cancels the view"""
        await interaction.message.delete()
        self.name = "cancel"
        self.stop()


class CategoryButton(nextcord.ui.Button):
    """A button representing a server."""

    def __init__(self, name, color=nextcord.ButtonStyle.gray, disabled=False):
        self.name = name
        super().__init__(
            label=name,
            style=color,
            disabled=disabled,
        )

    async def callback(self, _interaction: nextcord.Interaction):
        """Callback for when the button is pressed."""
        super().view.name = self.name
        super().view.stop()


class TeamGenerationView(nextcord.ui.View):
    """View to show generated teams."""

    def __init__(self, elo_disabled, balancing_disabled):
        super().__init__()
        if elo_disabled is True:
            self.children[1].disabled = True
        if balancing_disabled is True:
            self.children[2].disabled = True
        self.action = None

    @nextcord.ui.button(label="Move", style=nextcord.ButtonStyle.green)
    async def move(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Moves the players"""
        await _interaction.response.defer()
        self.action = "move"
        self.stop()

    @nextcord.ui.button(label="🔁 ELO", style=nextcord.ButtonStyle.gray)
    async def elo(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Moves the players"""
        await _interaction.response.defer()
        self.action = "elo"
        self.stop()

    @nextcord.ui.button(label="🔁 RGL Divisions", style=nextcord.ButtonStyle.gray)
    async def balance(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Rerolls new balanced teams"""
        await _interaction.response.defer()
        self.action = "balance"
        self.stop()

    @nextcord.ui.button(label="🔁 Random", style=nextcord.ButtonStyle.gray)
    async def random(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        "Rerolls new random teams"
        await _interaction.response.defer()
        self.action = "random"
        self.stop()


class MoveView(nextcord.ui.View):
    """View to show moving users back."""

    def __init__(self):
        super().__init__()
        self.action = None

    @nextcord.ui.button(label="Move Back", style=nextcord.ButtonStyle.gray)
    async def move_back(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Moves the players"""
        self.action = "move"
        self.stop()

    @nextcord.ui.button(label="Done", style=nextcord.ButtonStyle.green)
    async def done(
        self, _button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        """Rerolls new balanced teams"""
        await interaction.message.delete()
        self.action = "done"
        self.stop()


class BooleanView(nextcord.ui.View):
    """Simple view displaying Yes/No buttons."""

    def __init__(self):
        super().__init__()
        self.action = None

    @nextcord.ui.button(label="Yes", style=nextcord.ButtonStyle.green, row=0)
    async def yes_button(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Yes button that sets action to true"""
        self.action = True
        self.stop()

    @nextcord.ui.button(label="No", style=nextcord.ButtonStyle.red, row=1)
    async def no_button(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """No button that sets action to false"""
        self.action = False
        self.stop()


class ChannelSelect(nextcord.ui.View):
    """View to select pug channels."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.channel_id = None

    @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
    async def finish(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Continues setup"""
        self.action = "continue"
        self.stop()

    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red)
    async def cancel(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Cancels setup"""
        self.action = "cancel"
        self.stop()

    @nextcord.ui.channel_select(placeholder="Add up/selecting channel")
    async def channel(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select the channel that users will add up in.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.channel_id = channel.values[0].id
