"""Contains classes for registration of new users."""
import asyncio
from dataclasses import dataclass
import json

from database import BotCollection

guild_config_db: BotCollection = BotCollection("guilds", "config")


@dataclass
class RegistrationRoles:
    """Stores the role IDs for registration roles."""

    noexp: int | None = None
    newcomer: int | None = None
    amateur: int | None = None
    intermediate: int | None = None
    main: int | None = None
    advanced: int | None = None
    invite: int | None = None
    bypass: int | None = None
    ban: int | None = None
    registered: int | None = None


@dataclass
class RegistrationChannels:
    """Stores the channel IDs for registration channels."""

    registration: int | None = None
    logs: int | None = None


class RegistrationSettings:
    """Stores the registration settings for a guild."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.ban: bool = False
        self.bypass: bool = False
        self.gamemode: str = ""
        self.mode: str = ""
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
                    self.roles = RegistrationRoles(**value)
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
