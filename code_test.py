# https://docs.rgl.gg/league/references/maps_and_configs/

import aiohttp
import asyncio
import bs4
import database

SIXES_MAPS = {}
HL_MAPS = {}


async def test():
    serveme_api_key = database.get_server(168371563660443648)["serveme"]
    await get_new_reservation(serveme_api_key)


async def get_new_reservation(serveme_key: str):
    times = await get_reservation_times(serveme_key)
    headers = {"Content-type": "application/json"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            "https://na.serveme.tf/api/reservations/find_servers?api_key="
            + serveme_key,
            data=times,
            headers=headers,
        ) as resp:
            print(await resp.text())


async def get_reservation_times(serveme_key: str):
    headers = {"Content-type": "application/json"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            "https://na.serveme.tf/api/reservations/new?api_key=" + serveme_key
        ) as resp:
            times = await resp.text()
            return times


asyncio.run(test())
