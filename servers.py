from nextcord.ext import tasks, commands
from constants import *
from util import check_if_runner

import bs4
import aiohttp
import random
import database
import string
import nextcord

SIXES_MAPS = {}
HL_MAPS = {}

with open("maps.json") as json_file:
    maps: dict = json.load(json_file)


class ServerCog(commands.Cog):
    def __init__(self, bot: nextcord.Client):
        self.bot = bot
        self.mapUpdater.start()

    @tasks.loop(hours=4)
    async def mapUpdater(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://docs.rgl.gg/league/references/maps_and_configs/"
            ) as resp:
                html = await resp.text()
                soup = bs4.BeautifulSoup(html, "html.parser")
                map_marker = soup.find(id="custom-map-downloads")
                sixes_list = map_marker.find_next_sibling("ul")
                hl_list = sixes_list.find_next_sibling("ul")

                for map in sixes_list.find_all("li"):
                    SIXES_MAPS[map.text.rsplit("_", 1)[0]] = map.text

                for map in hl_list.find_all("li"):
                    HL_MAPS[map.text.rsplit("_", 1)[0]] = map.text

        print("Updated maps:\n" + str(SIXES_MAPS) + "\n" + str(HL_MAPS))

        map_dict = {"sixes": SIXES_MAPS, "hl": HL_MAPS}

        map_json = json.dumps(map_dict)

        with open("maps.json", "w") as outfile:
            outfile.write(map_json)

        # await self.bot.sync_all_application_commands(register_new=True)
        print("All app commands synced")

    async def get_new_reservation(self, serveme_key: str):
        times_json, times_text = await self.get_reservation_times(serveme_key)
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                "https://na.serveme.tf/api/reservations/find_servers?api_key="
                + serveme_key,
                data=times_text,
                headers=headers,
            ) as resp:
                servers = await resp.json()
                return servers, times_json

    async def get_reservation_times(self, serveme_key: str):
        headers = {"Content-type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                "https://na.serveme.tf/api/reservations/new?api_key=" + serveme_key
            ) as times:
                times_json = await times.json()
                times_text = await times.text()
                return times_json, times_text

    @nextcord.slash_command(name="reserve", guild_ids=TESTING_GUILDS)
    async def reserve_server(
        self,
        interaction: nextcord.Interaction,
        map: str = nextcord.SlashOption(
            name="map",
            choices=maps["sixes"] | maps["hl"],
        ),
        gamemode: str = nextcord.SlashOption(
            name="gamemode",
            choices={
                "6s": "sixes",
                "HL": "highlander",
            },
        ),
    ):
        print(gamemode)
        runner_req: bool = await check_if_runner(interaction.guild, interaction.user)
        if runner_req == False:
            await interaction.send("You do not have permission to run servers.")
            return

        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        servers, times = await self.get_new_reservation(serveme_api_key)

        for server in servers["servers"]:
            if "chi" in server["ip"]:
                if 536 != server["id"]:
                    print("New server reserved: " + str(server))
                    reserve = server
                    break

        connectPassword = "pug." + "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        rconPassword = "rcon.pug." + "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )

        if gamemode == "sixes":
            whitelist_id = 20  # 6s whitelist ID
            if map not in maps["sixes"].values():
                await interaction.send("Invalid map.")
                return
            if map.startswith("cp_"):
                server_config_id = 69  # rgl_6s_5cp_scrim
            else:
                server_config_id = 68  # rgl_6s_koth_bo5
        else:
            whitelist_id = 22  # HL whitelist ID
            if map not in maps["hl"].values():
                await interaction.send("Invalid map.")
                return
            if map.startswith("pl_"):
                server_config_id = 55
            else:
                server_config_id = 54

        reserveString = {
            "reservation": {
                "starts_at": times["reservation"]["starts_at"],
                "ends_at": times["reservation"]["ends_at"],
                "rcon": rconPassword,
                "password": connectPassword,
                "server_id": reserve["id"],
                "enable_plugins": True,
                "enable_demos_tf": True,
                "first_map": map,
                "server_config_id": server_config_id,
                "whitelist_id": whitelist_id,
                "custom_whitelist_id": None,
                "auto_end": True,
            }
        }

        reserve_JSON = json.dumps(reserveString)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://na.serveme.tf/api/reservations?api_key=" + serveme_api_key,
                data=reserve_JSON,
                headers={"Content-type": "application/json"},
            ) as resp:
                print(await resp.text())

        connect = (
            "connect " + reserve["ip_and_port"] + '; password "' + connectPassword + '"'
        )
        rcon = (
            "rcon_address "
            + reserve["ip_and_port"]
            + '; rcon_password "'
            + rconPassword
            + '"'
        )
        connectLink = (
            "steam://connect/" + reserve["ip_and_port"] + "/" + connectPassword
        )

        embed = nextcord.Embed(title="Server started!", color=0xF0984D)
        embed.add_field(name="Server", value=reserve["name"], inline=False)
        embed.add_field(name="Connect", value=connect, inline=False)
        embed.add_field(
            name="RCON", value="RCON has been sent in the rcon channel.", inline=False
        )
        embed.add_field(name="Map", value=map, inline=False)
        embed.set_footer(text=VERSION)
        await interaction.send(embed=embed)

        # RCON Message
        rcon_channel = self.bot.get_channel(guild_data["rcon"])
        await rcon_channel.send(rcon)

        # Connect Message
        connect_channel = self.bot.get_channel(guild_data["connect"])
        connectEmbed = nextcord.Embed(title=connectLink, color=0x3DFF1F)
        connectEmbed.add_field(name="Command", value=connect, inline=False)
        await connect_channel.send(embed=connectEmbed)
