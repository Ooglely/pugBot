"""Class used to interact with the serveme.tf API."""
import json
from datetime import datetime, timedelta

import aiohttp


class ServemeAPI:
    """Class used to interact with the serveme.tf API."""

    def __init__(self):
        self.base_url = "https://na.serveme.tf/api/reservations/"

    async def get_new_reservation(
        self, serveme_key: str, start_time: datetime | None = None, duration: float = 2
    ):
        """Gets a new reservation from na.serveme.tf.

        Args:
            serveme_key (str): The serveme.tf API key.
            start_time (datetime): Optional time for the server to start
            duration (float): Optional length of the reservation

        Returns:
            dict: The reservation data.
        """

        times_json: dict
        times_text: str
        if not start_time:
            # No start time provided, get current time
            times_json, times_text = await self.get_reservation_times(serveme_key)

            # Adjust duration
            if duration != 2:
                ends_at = datetime.fromisoformat(times_json["reservation"]["starts_at"])
                ends_at += timedelta(hours=duration)
                times_json["reservation"]["ends_at"] = ends_at.isoformat()
                times_text = json.dumps(times_json)
        else:
            # Custom start time
            times_json = {
                "reservation": {
                    "starts_at": start_time.isoformat(),
                    "ends_at": (start_time + timedelta(hours=duration)).isoformat(),
                }
            }
            times_text = json.dumps(times_json)

        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                self.base_url + "find_servers?api_key=" + serveme_key,
                data=times_text,
                headers=headers,
            ) as resp:
                servers = await resp.json(content_type=None)
                return servers, times_json

    async def get_reservation_times(self, serveme_key: str):
        """Gets the reservation times from na.serveme.tf.

        Args:
            serveme_key (str): The serveme.tf API key.

        Returns:
            dict: The reservation times.
        """
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                self.base_url + "new?api_key=" + serveme_key
            ) as times:
                times_json = await times.json()
                times_text = await times.text()
                return times_json, times_text

    async def get_current_reservations(self, serveme_key: str):
        """Gets the current reservations from na.serveme.tf.

        Args:
            serveme_key (str): The serveme.tf API key.

        Returns:
            dict: The current reservations.
        """
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(self.base_url + "?api_key=" + serveme_key) as times:
                reservations = await times.json()
                active_servers = []
                future_servers = []
                for reservation in reservations["reservations"]:
                    if (
                        reservation["status"] != "Ended"
                        and reservation["status"] == "Waiting to start"
                    ):
                        active_servers.append(reservation)
                    elif reservation["status"] == "Waiting to start":
                        future_servers.append(reservation)
                active_servers.reverse()
                return active_servers, future_servers
