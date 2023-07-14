"""Holds classes for pug commands/setup"""
import nextcord

default_category = {
    "name": "",
    "add_up": None,
    "red_team": None,
    "blu_team": None,
    "first_to": {
        "enabled": False,
        "num": 0,
    },
}


class PugCategory:
    """Represents a pug category, settings and channel for a section of pugs"""

    def __init__(
        self, category=default_category
    ):  # pylint: disable=dangerous-default-value
        self.name: str = category["name"]
        self.add_up: int = category["add_up"]
        self.red_team: int = category["red_team"]
        self.blu_team: int = category["blu_team"]
        self.first_to = category["first_to"]


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
        self.first_to = None

    @nextcord.ui.channel_select(
        custom_id="first_to", placeholder="Select a channel to move players to"
    )
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
        self.name = None


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
