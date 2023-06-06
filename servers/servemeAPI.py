import aiohttp
import asyncio
import database


class servemeAPI:
    def __init__(self):
        self.baseURL = "https://na.serveme.tf/api/reservations/"

    async def get_new_reservation(self, serveme_key: str):
        times_json, times_text = await self.get_reservation_times(serveme_key)
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                self.baseURL + "find_servers?api_key=" + serveme_key,
                data=times_text,
                headers=headers,
            ) as resp:
                servers = await resp.json()
                return servers, times_json

    async def get_reservation_times(self, serveme_key: str):
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                self.baseURL + "new?api_key=" + serveme_key
            ) as times:
                times_json = await times.json()
                times_text = await times.text()
                return times_json, times_text

    async def get_current_reservations(self, serveme_key: str):
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(self.baseURL + "?api_key=" + serveme_key) as times:
                reservations = await times.json()
                active_servers = []
                for reservation in reservations["reservations"]:
                    if reservation["status"] != "Ended":
                        active_servers.append(reservation)
                active_servers.reverse()
                return active_servers


async def test_func():
    guild_data = database.get_server(168371563660443648)
    serveme_api_key = guild_data["serveme"]
    test_result = await servemeAPI().get_current_reservations(serveme_api_key)
    print(test_result)


if __name__ == "__main__":
    asyncio.run(test_func())