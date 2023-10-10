"""File storing the LogsAPI class, which is used to interact with the Logs.tf API."""
import aiohttp

BASE_URL = "https://logs.tf/api/v1/"


class LogsAPI:
    """Class used to interact with the Logs.tf API."""

    def __init__(self) -> None:
        pass

    @staticmethod
    async def get_single_log(log_id: int) -> dict:
        """Return the log data of a singular log from logs.tf.

        Args:
            log_id (int): The ID of the log to get.

        Returns:
            dict: The log data.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}log/{str(log_id)}") as resp:
                log = await resp.json()
                return log

    @staticmethod
    async def search_for_log(
        title: str | None = None,
        map_name: str | None = None,
        uploader: int | None = None,
        players: list[int] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict:
        """Search for a log on logs.tf.

        http://logs.tf/api/v1/log?title=X&uploader=Y&player=Z&limit=N&offset=N

        Available filters (copied from logs.tf API docs):\n
        title           Title text search (min. 2 characters)
        map	            Exact name of a map
        uploader	    Uploader SteamID64
        player	        One or more player SteamID64 values, comma-separated
        limit	        Limit results (default 1000, maximum 10000)
        offset	        Offset results (default 0)

        Returns:
            dict: The log query.
        """
        query_url = f"{BASE_URL}log?"
        if title is not None:
            query_url += f"title={title}&"

        if map_name is not None:
            query_url += f"map={map_name}&"

        if uploader is not None:
            query_url += f"uploader={uploader}&"

        if players is not None:
            steam_ids = ""
            for steam_id in players:
                steam_ids += f"{steam_id},"

            steam_ids = steam_ids[:-1]
            query_url += f"player={steam_ids}&"

        if limit is not None:
            query_url += f"limit={limit}&"

        if offset is not None:
            query_url += f"offset={offset}&"

        async with aiohttp.ClientSession() as session:
            async with session.get(query_url) as resp:
                log = await resp.json()
                return log
