"""Class used to interact with the serveme.tf API."""

import json
import re
from datetime import datetime, timedelta
from typing import no_type_check, Dict

import aiohttp

from constants import SERVEME_API_KEY

with open("maps.json", encoding="UTF-8") as json_file:
    maps_dict: dict = json.load(json_file)
    COMP_MAPS = maps_dict["sixes"] | maps_dict["hl"]


def update_comp_maps(map_dict: dict) -> None:
    """Update the list of comp maps for the map searcher"""
    global COMP_MAPS
    COMP_MAPS = map_dict["sixes"] | map_dict["hl"]
    print(COMP_MAPS)


class ServemeAPI:
    """Class used to interact with the serveme.tf API."""

    def __init__(self):
        self.base_url = "https://na.serveme.tf/api/reservations/"

    async def get_server_list(
        self, serveme_key: str, start_time: datetime | None = None, duration: float = 2
    ):
        """Gets the list of servers from na.serveme.tf.

        Args:
            serveme_key (str): The serveme.tf API key.
            start_time (datetime): Optional time for the server to start
            duration (float): Optional length of the reservation

        Returns:
            dict: The server data.
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

    async def reserve_server(self, serveme_key: str, reservation_data: dict):
        """
        Reserve a new server
        :param serveme_key: The api key to reserve with
        :param reservation_data: Dict with the desired reservation information
        :return: JSON of the response
        """
        reserve_json = json.dumps(reservation_data)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + "?api_key=" + serveme_key,
                data=reserve_json,
                headers={"Content-type": "application/json"},
            ) as resp:
                server_data = await resp.json()
                print(server_data)
                return server_data

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
                times_text = await times.text()
                times_json = await times.json()
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
                        and reservation["status"] != "Waiting to start"
                    ):
                        active_servers.append(reservation)
                    elif reservation["status"] == "Waiting to start":
                        future_servers.append(reservation)
                active_servers.reverse()
                return active_servers, future_servers

    @staticmethod
    async def fetch_all_maps() -> list[str]:
        """Fetches all maps from the serveme.tf FastDL and updates the cached list.

        Returns:
            list: A list of all maps.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://na.serveme.tf/api/maps?api_key={SERVEME_API_KEY}"
            ) as resp:
                data = await resp.json()
                if data is None:
                    return []
                return list(data["maps"])

    @staticmethod
    @no_type_check  # LOLLLLL
    async def fetch_newest_version(map_name: str, maps_list: list) -> list[str] | None:
        """Fetches the newest version of a map from the serveme.tf FastDL.

        Args:
            map_name (str): The name of the map.
            maps_list

        Returns:
            list[str]: The newest version of the map.
            None: if no matching map is found.
        """
        if map_name in COMP_MAPS:
            return [COMP_MAPS[map_name]]

        # Get all maps that match the name
        # maps = re.findall(rf"{map_name}.*", maps_list)
        match_regex = re.compile(rf"{map_name}.*")
        maps = set(filter(match_regex.match, maps_list))

        # If there's only one map, return it
        if len(maps) == 0:
            return None
        if len(maps) == 1:
            return list(maps)
        # For each different type, get the newest version
        versions: Dict[str, str] = {}
        for map_version in maps:
            version_name = re.search(rf"(?<={map_name})(.*)", map_version).group(0)
            version_number = re.search(r"\d*(?=$)", version_name)
            version_type = re.search(r"^.*(?<!(\d))", version_name)
            if version_number is not None:
                version_number = version_number.group(0)
            version_type = version_type.group(0)

            if version_type in versions:
                if versions[version_type] == "" or version_number == "":
                    versions[version_type] = version_number
                elif int(version_number) > int(versions[version_type]):
                    versions[version_type] = version_number
            else:
                versions[version_type] = version_number

        newest_versions = [
            f"{map_name}{letter}{num}" for letter, num in versions.items()
        ]
        return newest_versions

    @staticmethod
    async def check_whitelist_status() -> bool:
        """
        Checks if whitelist.tf is working as expected
        Returns:
            bool: Working as expected, or not
        """

        async with aiohttp.ClientSession() as session:
            async with session.get("https://whitelist.tf") as resp:
                if resp.status < 300:
                    return True
        return False


if __name__ == "__main__":
    import asyncio

    map_list = asyncio.run(ServemeAPI.fetch_all_maps())
    print(map_list)
    print(asyncio.run(ServemeAPI.check_whitelist_status()))
    print(
        f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('pass_arena', map_list))}"
    )
    print(
        f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('dkhgjfdshg', map_list))}"
    )
    print(
        f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('koth_product', map_list))}"
    )
    print(
        f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('cp_proces', map_list))}"
    )
