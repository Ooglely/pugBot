"""Contains classes for registration of new users."""
import asyncio
from dataclasses import dataclass
import json

from database import BotCollection

guild_config_db: BotCollection = BotCollection("guilds", "config")


@dataclass
class DivisionRoles:
    """Stores role IDs for each RGL division."""

    noexp: int | None = None
    newcomer: int | None = None
    amateur: int | None = None
    intermediate: int | None = None
    main: int | None = None
    advanced: int | None = None
    invite: int | None = None

    def __str__(self) -> str:
        return f"No Experience: <@&{self.noexp}>\nNewcomer: <@&{self.newcomer}>\nAmateur: <@&{self.amateur}>\nIntermediate: <@&{self.intermediate}>\nMain: <@&{self.main}>\nAdvanced: <@&{self.advanced}>\nInvite: <@&{self.invite}>"


@dataclass
class RegistrationRoles:
    """Stores the role IDs for registration roles."""

    sixes: DivisionRoles = DivisionRoles()
    highlander: DivisionRoles = DivisionRoles()
    bypass: int | None = None
    ban: int | None = None
    registered: int | None = None


@dataclass
class RegistrationChannels:
    """Stores the channel IDs for registration channels."""

    registration: int | None = None
    logs: int | None = None

    def __str__(self) -> str:
        return f"Registration: <#{self.registration}>\nLogs: <#{self.logs}>"


class RegistrationSettings:
    """Stores the registration settings for a guild."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.ban: bool = False
        self.bypass: bool = False
        self.gamemode: str = "None"
        self.mode: str = "None"
        self.roles: RegistrationRoles = RegistrationRoles()
        self.channels: RegistrationChannels = RegistrationChannels()

    def to_dict(self):
        """Convert the settings to a dictionary.

        Returns
        -------
        dict
            The object as a dictionary
        """
        return json.loads(json.dumps(self, default=lambda o: o.__dict__))

    async def load_data(self, guild_id: int) -> None:
        """Load the registration settings from the database."""
        try:
            config: dict = await guild_config_db.find_item({"guild": guild_id})
        except LookupError:
            return

        if "registration" in config:
            reg_settings: dict = config["registration"]
            for key, value in reg_settings.items():
                if key == "roles":
                    # First need to check if its using the old role storage or not
                    if (
                        "sixes" in reg_settings["roles"]
                        and "highlander" in reg_settings["roles"]
                    ):
                        # New role storage
                        self.roles.sixes = DivisionRoles(
                            **reg_settings["roles"]["sixes"]
                        )
                        self.roles.highlander = DivisionRoles(
                            **reg_settings["roles"]["highlander"]
                        )
                    else:
                        # Old role storage
                        division_roles = DivisionRoles(
                            reg_settings["roles"]["noexp"],
                            reg_settings["roles"]["newcomer"],
                            reg_settings["roles"]["amateur"],
                            reg_settings["roles"]["intermediate"],
                            reg_settings["roles"]["main"],
                            reg_settings["roles"]["advanced"],
                            reg_settings["roles"]["invite"],
                        )
                        setattr(self.roles, reg_settings["gamemode"], division_roles)
                    # Then add the rest of the roles
                    self.roles.registered = reg_settings["roles"]["registered"]
                    self.roles.ban = reg_settings["roles"]["ban"]
                    self.roles.bypass = reg_settings["roles"]["bypass"]
                elif key == "channels":
                    self.channels = RegistrationChannels(**value)
                else:
                    setattr(self, key, value)

    async def upload_data(self, guild_id: int) -> None:
        """Upload the registration settings to the database."""
        try:
            await guild_config_db.find_item({"guild": guild_id})
            await guild_config_db.update_item(
                {"guild": guild_id}, {"$set": {"registration": self.to_dict()}}
            )
        except LookupError:
            await guild_config_db.add_item(
                {"guild": guild_id, "registration": self.to_dict()}
            )
