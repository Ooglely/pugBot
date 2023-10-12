"""Holds classes for pug commands/setup"""
from typing import Union, List, Dict

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


class Player:
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
        self.steam: int = player_data["steam"]
        self.discord: int = player_data["discord"]
        self.division: Dict[str, Dict[str, int]] = player_data["divison"]
        self.registered: bool = registered


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

    async def get_last_players(self, guild: int) -> List[Player] | None:
        """Gets the last players from the database."""
        try:
            result = await category_db.find_item({"_id": guild})
        except LookupError:
            return None
        print(result["categories"])
        if (
            self.name not in result["categories"]
            or "players" not in result["categories"][self.name]
        ):
            return None
        players: List[Player] = []
        for player in result["categories"][self.name]["players"]:
            print(player)
            players.append(Player(player["steam"]))
        return players

    async def update_last_players(self, guild: int, players: List[Player]) -> None:
        """Updates the last players in the database."""
        last_players = []
        for player in players:
            last_players.append(player.__dict__)
        await category_db.update_item(
            {"_id": guild},
            {"$set": {f"categories.{self.name}.players": last_players}},
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

    def __init__(self, balancing_disabled):
        super().__init__()
        self.balancing_disabled = balancing_disabled
        if balancing_disabled:
            self.children[1].disabled = True
        self.action = None

    @nextcord.ui.button(label="Move", style=nextcord.ButtonStyle.green)
    async def move(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Moves the players"""
        self.action = "move"
        self.stop()

    @nextcord.ui.button(label="Reroll Balanced Teams", style=nextcord.ButtonStyle.gray)
    async def balance(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Rerolls new balanced teams"""
        self.action = "balance"
        self.stop()

    @nextcord.ui.button(label="Reroll Random Teams", style=nextcord.ButtonStyle.gray)
    async def random(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        "Rerolls new random teams"
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
