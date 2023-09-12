"""File storing the LogsAPI class, which is used to interact with the Logs.tf API."""
import aiohttp

baseURL = "https://logs.tf/api/v1/"


class LogsAPI:
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
            async with session.get(f"{baseURL}log/{str(log_id)}") as resp:
                log = await resp.json()
                return log
