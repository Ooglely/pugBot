"""Classes for use in the servers cog."""
import asyncio
from datetime import datetime
from typing import Optional

import nextcord
import pytz
import aiohttp
from rcon import WrongPassword
from rcon.source import rcon

from database import get_steam_from_discord
from servers.serveme_api import ServemeAPI


class Servers(nextcord.ui.View):
    """Displays the current servers and allows the user to select one."""

    def __init__(self):
        super().__init__()
        self.server_chosen = None


class ServerButton(nextcord.ui.Button):
    """A button representing a server."""

    def __init__(self, reservation, num, highlighted=True):
        self.num = num
        text = f"ID #{reservation['id']} - {reservation['server']['name']}"
        if reservation["status"] == "Waiting to start":
            text += f" - Opens: {datetime.fromisoformat(reservation['starts_at']).astimezone(pytz.timezone('US/Eastern')).strftime('%m-%d %H:%M:%S')}"

        if highlighted:
            color = nextcord.ButtonStyle.green
        else:
            color = nextcord.ButtonStyle.gray

        super().__init__(
            label=text,
            custom_id=str(num),
            style=color,
        )

    async def callback(self, _interaction: nextcord.Interaction):
        """Callback for when the button is pressed."""
        if self.view is not None:
            self.view.server_chosen = self.num
            self.view.stop()


class Reservation:
    """
    Represents a reservation on na.serveme.tf
    Hashable on the unique reservation id

    Attributes:
        reservation_id (int): The ID of the reservation
        api_key (str): The API key associated with the reservation
        guild (int): The associated guild id
        messages (list[tuple[int]]): List of the channel and message ids associated with this reservation
        category (Optional[str]): The associated category name
    """

    def __init__(self, reservation_id: int, api_key: str, guild: int, messages, connect_channel_id = None) -> None:
        self.reservation_id = reservation_id
        self.api_key = api_key
        self.messages = messages
        self.guild: int = guild
        self.connect_channel_id = connect_channel_id

    def __hash__(self):
        return hash(self.reservation_id)

    def __eq__(self, other):
        return type(other) is type(self) and self.reservation_id == other.reservation_id

    async def is_active(self) -> bool | None:
        """Checks if the reservation is still active

        Returns:
            bool: True if active, False ended, None if no response or other error
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://na.serveme.tf/api/reservations/{self.reservation_id}?api_key={self.api_key}",
            ) as resp:
                server = await resp.json()
                if server is None:
                    return None
                print("Reservation info:", server)
                if server["reservation"]["status"] == "Ended":
                    return False
                return True

    async def stop_tracking(self, bot: nextcord.Client):
        """Deletes the reservation messages and stops tracking the reservation.

        Args:
            bot (nextcord.Client): The bot instance.
        """
        for message in self.messages:
            try:
                guild: nextcord.Guild | None = bot.get_guild(self.guild)
                if guild is not None:
                    channel: Optional[nextcord.abc.GuildChannel] = guild.get_channel(
                        message[0]
                    )
                    if isinstance(channel, nextcord.TextChannel):
                        guild_message: nextcord.Message = await channel.fetch_message(
                            message[1]
                        )
                        await guild_message.delete()
                    else:
                        print(
                            f"Couldn't delete reservation message: Channel {message[0]} not found in guild {guild}, likely due to permission issues."
                        )
            except nextcord.HTTPException as err:
                print(f"Couldn't delete reservation message: {err}\n{message}")

    async def toggle_player_whitelist(self, enabled: bool):
        command = f"sm_game_player_whitelist {1 if enabled else 0}"
    
        retries = 50
        timeout = 2
        count = 0

        while count < retries:
            await asyncio.sleep(timeout)
            reservation = (await ServemeAPI().get_reservation_by_id(self.api_key, self.reservation_id))
            count += 1

            print(reservation['status'])

            try:
                response = await rcon(
                    command=command,
                    host=reservation["server"]["ip"],
                    port=int(reservation["server"]["port"]),
                    passwd=reservation["rcon"],
                )
                break
            except (ConnectionRefusedError, WrongPassword) as e:
                pass
        else:
            print(f"Player whitelist not able to be started for reservation {self.reservation_id}: Server Status {reservation['status']}")
            return

        print(f"{"Enabled" if enabled else "Disabled"} player whitelist for reservation {self.reservation_id}")

    async def add_to_whitelist(self, member: nextcord.Member):
        steam_id = await get_steam_from_discord(member.id)

        command = f"sm_game_player_add {steam_id}"

        retries = 50
        timeout = 2
        count = 0

        while count < retries:
            await asyncio.sleep(timeout)
            reservation = (await ServemeAPI().get_reservation_by_id(self.api_key, self.reservation_id))
            count += 1

            try:
                response = await rcon(
                    command=command,
                    host=reservation["server"]["ip"],
                    port=int(reservation["server"]["port"]),
                    passwd=reservation["rcon"],
                )
                break
            except (ConnectionRefusedError, WrongPassword) as e:
                pass
        else:
            print(f"Player not able to be added to whitelist for reservation {self.reservation_id}: Server Status {reservation['status']}")
            return

        response = await rcon(
            command=command,
            host=reservation["server"]["ip"],
            port=int(reservation["server"]["port"]),
            passwd=reservation["rcon"],
        )

        print(f"Added member {member} to reservation {self.reservation_id}")

    async def remove_from_whitelist(self, member: nextcord.Member):
        steam_id = await get_steam_from_discord(member.id)

        command = f"sm_game_player_del {steam_id}"
        
        retries = 50
        timeout = 2
        count = 0

        while count < retries:
            await asyncio.sleep(timeout)
            reservation = (await ServemeAPI().get_reservation_by_id(self.api_key, self.reservation_id))
            count += 1

            try:
                response = await rcon(
                    command=command,
                    host=reservation["server"]["ip"],
                    port=int(reservation["server"]["port"]),
                    passwd=reservation["rcon"],
                )
                break
            except (ConnectionRefusedError, WrongPassword) as e:
                pass
        else:
            print(f"Player not able to be added to whitelist for reservation {self.reservation_id}: Server Status {reservation['status']}")
            return

        response = await rcon(
            command=command,
            host=reservation["server"]["ip"],
            port=int(reservation["server"]["port"]),
            passwd=reservation["rcon"],
        )

        print(f"Removed member {member} to reservation {self.reservation_id}")


class MapSelection(nextcord.ui.View):
    """Displays the different map options and allows the user to select one."""

    def __init__(self, maps: list[str]):
        super().__init__()
        self.map_chosen: str = ""

        for map_name in maps:
            super().add_item(MapButton(map_name))


class MapButton(nextcord.ui.Button):
    """A button representing a map."""

    def __init__(self, map_name: str):
        self.map = map_name
        super().__init__(
            label=map_name,
            custom_id=map_name,
            style=nextcord.ButtonStyle.green,
        )

    async def callback(self, _interaction: nextcord.Interaction):
        """Callback for when the button is pressed."""
        if self.view is not None:
            self.view.map_chosen = self.map
            self.view.stop()
