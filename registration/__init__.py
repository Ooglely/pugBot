"""Holds views for the registration commands."""
import nextcord

from database import get_server, set_registration_settings


class RegistrationSettings:
    """A base class for registration settings for a server."""

    def __init__(self):
        self.enabled: bool = False
        self.ban: bool = False
        self.bypass: bool = False
        self.gamemode: str = ""
        self.mode: str = ""
        self.roles: dict[str, int | None] = {
            "noexp": None,
            "newcomer": None,
            "amateur": None,
            "intermediate": None,
            "main": None,
            "advanced": None,
            "invite": None,
            "bypass": None,
            "ban": None,
        }
        self.channels: dict[str, int | None] = {"registration": None, "logs": None}

    def import_from_db(self, guild: int):
        """Imports the registration settings for the server from the database.

        Args:
            guild (int): The guild ID to get.
        """
        server = get_server(guild)
        if "registration" in server:
            print(server["registration"])
            self.enabled = server["registration"]["enabled"]
            self.ban = server["registration"]["ban"]
            self.bypass = server["registration"]["bypass"]
            self.gamemode = server["registration"]["gamemode"]
            self.mode = server["registration"]["mode"]
            self.roles = server["registration"]["roles"]
            self.channels = server["registration"]["channels"]

    def export_to_db(self, guild: int):
        """Exports the registration settings for the server to the database.

        Args:
            guild (int): The guild ID to set.
        """
        set_registration_settings(guild, self.__dict__)


class SetupIntroduction(nextcord.ui.View):
    """View to introduce the registration setup process."""

    def __init__(self):
        super().__init__()
        self.action = None

    @nextcord.ui.button(label="Setup & Enable", style=nextcord.ButtonStyle.green)
    async def enable(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Enables registration."""
        self.action = "enable"
        self.stop()

    @nextcord.ui.button(label="Disable", style=nextcord.ButtonStyle.red)
    async def disable(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Disables registration."""
        self.action = "disable"
        self.stop()

    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.grey)
    async def cancel(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Cancels setup"""
        self.action = "cancel"
        self.stop()


class RegistrationRoles(nextcord.ui.View):
    """Set division roles in the registration process."""

    def __init__(self, divisions, roles):
        super().__init__()
        for division in divisions:
            self.add_item(DivisionRoleSelect(division))
        self.action = None
        self.roles = roles

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


class DivisionRoleSelect(nextcord.ui.RoleSelect):
    """A role select for division roles."""

    def __init__(self, division: str):
        if division == "noexp":
            super().__init__(placeholder="No Experience", max_values=1)
        else:
            super().__init__(placeholder=f"{division.capitalize()} role", max_values=1)
        self.division = division

    async def callback(self, _interaction: nextcord.Interaction):
        """Sets the role in the view to the selected role."""
        super().view.roles[self.division] = self.values[0].id


class GamemodeSelect(nextcord.ui.View):
    """A view to select the gamemode for registration. This chooses the gamemode divisions to look at."""

    def __init__(self):
        super().__init__()
        self.selection: str = ""

    @nextcord.ui.button(label="6s", style=nextcord.ButtonStyle.grey)
    async def sixes(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects 6s as the gamemode"""
        self.selection = "sixes"
        self.stop()

    @nextcord.ui.button(label="Highlander", style=nextcord.ButtonStyle.grey)
    async def highlander(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects HL as the gamemode"""
        self.selection = "highlander"
        self.stop()


class ModeSelect(nextcord.ui.View):
    """A view to select the mode for registration."""

    def __init__(self):
        super().__init__()
        self.selection: str = ""

    @nextcord.ui.button(label="Highest", style=nextcord.ButtonStyle.grey)
    async def highest(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects highest as the mode"""
        self.selection = "highest"
        self.stop()

    @nextcord.ui.button(label="Current", style=nextcord.ButtonStyle.grey)
    async def current(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Selects current as the mode"""
        self.selection = "current"
        self.stop()


class TrueFalseSelect(nextcord.ui.View):
    """A view to select the ban for registration."""

    def __init__(self):
        super().__init__()
        self.selection: bool = False

    @nextcord.ui.button(label="yes", style=nextcord.ButtonStyle.green)
    async def yes_ban(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Goes to the ban role selection menu"""
        self.selection = True
        await _interaction.response.edit_message(view=None)
        self.stop()

    @nextcord.ui.button(label="no", style=nextcord.ButtonStyle.red)
    async def no_ban(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Cancels ban role setup"""
        self.selection = False
        await _interaction.response.edit_message(view=None)
        self.stop()


class ChannelSelect(nextcord.ui.View):
    """View to select registration/logs channels."""

    def __init__(self):
        super().__init__()
        self.registration = None
        self.logs = None

    @nextcord.ui.channel_select(
        custom_id="registration", placeholder="Select a registration channel"
    )
    async def registration(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel to send new registrations to.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.registration = channel.values[0].id
        if self.logs is not None:
            self.stop()

    @nextcord.ui.channel_select(placeholder="Select a logs channel")
    async def logs(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel to send bot logs to.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.logs = channel.values[0].id
        if self.registration is not None:
            self.stop()
