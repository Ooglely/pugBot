"""Class used to interact with the serveme.tf API."""
import json
import re
from datetime import datetime, timedelta
from typing import Dict, no_type_check

import aiohttp

with open("maps.json", encoding="UTF-8") as json_file:
    maps_dict: dict = json.load(json_file)
    COMP_MAPS = maps_dict["sixes"] | maps_dict["hl"]


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
                        and reservation["status"] != "Waiting to start"
                    ):
                        active_servers.append(reservation)
                    elif reservation["status"] == "Waiting to start":
                        future_servers.append(reservation)
                active_servers.reverse()
                return active_servers, future_servers

    @staticmethod
    async def fetch_all_maps(map_names_only: bool = True):
        """Fetches all maps from the serveme.tf FastDL and updates the cached list.

        Returns:
            list: A list of all maps.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get("http://dl.serveme.tf/maps/") as resp:
                maps = await resp.text()
                if map_names_only:
                    return re.findall(r"(?<=>)(.*?)(?=.bsp)", maps)
                return maps

    @staticmethod
    @no_type_check  # LOLLLLL
    async def fetch_newest_version(map_name: str, maps_list: list = None):
        """Fetches the newest version of a map from the serveme.tf FastDL.

        Args:
            map_name (str): The name of the map.

        Returns:
            str: The newest version of the map.
            None: if no matching map is found.
        """
        if map_name in COMP_MAPS:
            return COMP_MAPS[map_name]
        async with aiohttp.ClientSession() as session:
            async with session.get("http://dl.serveme.tf/maps/") as resp:
                map_list = await resp.text()

        # Get all maps that match the beginning of the input
        if maps_list is None:
            maps = re.findall(rf"(?<=>)({map_name}.*)(?=.bsp)", map_list)
        else:  # If maps_list is provided, use that
            maps = re.findall(rf"(?<=>)({map_name}.*)(?=.bsp)", maps_list)
        # Deduplicate results
        maps_set = set(maps)
        print(maps_set)
        # If there's only one map, return it
        if len(maps_set) == 0:
            return None
        if len(maps_set) == 1:
            return maps_set.pop()
        # For each different type, get the newest version
        versions: Dict[str, str] = {}
        for map_version in maps_set:
            version_name = re.search(rf"(?<={map_name})(.*)", map_version).group(0)
            version_number = re.search(r"\d*(?=$)", version_name)
            version_type = re.search(r"^.*(?<!(\d))", version_name)
            if version_number is not None:
                version_number = version_number.group(0)
            else:
                version_number = None
            version_type = version_type.group(0)
            if version_type in versions:
                if versions[version_type] == "" or version_number == "":
                    versions[version_type] = version_number
                elif int(version_number) > int(versions[version_type]):
                    versions[version_type] = version_number
            else:
                versions[version_type] = version_number
        newest_versions = [f"{map_name}{type}{num}" for type, num in versions.items()]
        if len(newest_versions) == 1:
            return newest_versions.pop()
        return newest_versions


if __name__ == "__main__":
    import asyncio

    print(f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('pass_arena'))}")
    print(f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('dkhgjfdshg'))}")
    print(f"Result: {asyncio.run(ServemeAPI.fetch_newest_version('koth_product'))}")
    print(asyncio.run(ServemeAPI.fetch_all_maps()))
