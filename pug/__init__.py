"""Holds classes for pug commands/setup"""
from typing import Union, List, Dict, TypedDict
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
        self.icon: str | None = None

    def get_division(self, gamemode: str, mode: str) -> int:
        """Gets the division for the player."""
        if gamemode == "combined":
            return max(self.division["sixes"][mode], self.division["hl"][mode])
        if gamemode == "highlander":
            return self.division["hl"][mode]
        if gamemode == "sixes":
            return self.division["sixes"][mode]
        raise ValueError("Invalid gamemode")


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

    def __init__(
        self, name: str, color=nextcord.ButtonStyle.gray, disabled: bool = False
    ):
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


class Teams(TypedDict):
    """TypedDict for generated team storage."""

    red: List[PugPlayer]
    blu: List[PugPlayer]
