"""Class used to interact with the serveme.tf API."""
import aiohttp


class ServemeAPI:
    """Class used to interact with the serveme.tf API."""

    def __init__(self):
        self.base_url = "https://na.serveme.tf/api/reservations/"

    async def get_new_reservation(self, serveme_key: str):
        """Gets a new reservation from na.serveme.tf.

        Args:
            serveme_key (str): The serveme.tf API key.

        Returns:
            dict: The reservation data.
        """
        times_json, times_text = await self.get_reservation_times(serveme_key)
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                self.base_url + "find_servers?api_key=" + serveme_key,
                data=times_text,
                headers=headers,
            ) as resp:
                servers = await resp.json()
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
                for reservation in reservations["reservations"]:
                    if reservation["status"] != "Ended" and reservation["status"] != "Waiting to start":
                        active_servers.append(reservation)
                active_servers.reverse()
                return active_servers
