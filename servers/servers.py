from nextcord.ext import tasks, commands, application_checks
from constants import *
from servers.servemeAPI import servemeAPI
from rcon.source import Client

import bs4
import aiohttp
import random
import database
import string
import nextcord
import util

with open("maps.json") as json_file:
    maps: dict = json.load(json_file)
    SIXES_MAPS: dict = maps["sixes"]
    HL_MAPS: dict = maps["hl"]


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

        await self.bot.sync_all_application_commands(update_known=True)
        print("All app commands synced")

    @commands.Cog.listener("on_application_command_error")
    async def handle_errors(self, interaction: nextcord.Interaction, error: Exception):
        if error.__class__ == application_checks.ApplicationMissingRole:
            await interaction.send(
                "You are missing the runner role to be able to use this command.\n"
                + str(error)
            )
        elif error.__class__ == util.ServerNotSetupError:
            await interaction.send(
                "This server has not been set up for bot usage yet; please run the /setup command.\n"
                + str(error)
            )
        elif error.__class__ == util.NoServemeKey:
            await interaction.send(
                "This server has not been set up with a serveme.tf API key yet; please run the /serveme command.\n"
            )
        else:
            await interaction.send("An error has occurred.\n" + str(error))

    @nextcord.slash_command(name="reserve", guild_ids=TESTING_GUILDS)
    @util.is_setup()
    @util.is_runner()
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
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        servers, times = await servemeAPI().get_new_reservation(serveme_api_key)

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
        connectEmbed.add_field(name="Connect Link", value=connectLink, inline=False)
        await connect_channel.send(embed=connectEmbed)

    @util.is_setup()
    @util.is_runner()
    @nextcord.slash_command(name="map", guild_ids=TESTING_GUILDS)
    async def change_map(
        self,
        interaction: nextcord.Interaction,
        map: str = nextcord.SlashOption(
            name="map",
            choices=maps["sixes"] | maps["hl"],
        ),
    ):
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = await servemeAPI().get_current_reservations(serveme_api_key)

        if len(reservations) == 0:
            await interaction.send(
                "There are no active reservations with the associated serveme account."
            )
            return
        elif len(reservations) == 1:
            try:
                command: str = await util.get_exec_command(reservations[0], map)
            except Exception:
                await interaction.send(
                    "Unable to detect the current gamemode. The whitelist on the server is not associated with a gamemode."
                )
                return

            with Client(
                reservations[0]["server"]["ip"],
                int(reservations[0]["server"]["port"]),
                passwd=reservations[0]["rcon"],
            ) as client:
                client.run(command)

            await interaction.send("Changing map to " + map + ".")
            return
        else:

            class Servers(nextcord.ui.View):
                def __init__(self):
                    super().__init__()
                    self.server_chosen = None

            class ServerButton(nextcord.ui.Button):
                def __init__(self, reservation, num):
                    self.num = num
                    super().__init__(
                        label=f"ID #{reservation['id']} - {reservation['server']['name']}",
                        custom_id=str(num),
                        style=nextcord.ButtonStyle.blurple,
                    )

                async def callback(self, interaction: nextcord.Interaction):
                    super().view.server_chosen = self.num
                    super().view.stop()

            view = Servers()

            for num, reservation in enumerate(reservations):
                button = ServerButton(reservation, num)
                view.add_item(button)

            await interaction.send(
                "Select a reservation to change the map on.", view=view
            )
            await view.wait()
            server_id = view.server_chosen

            try:
                command: str = await util.get_exec_command(reservations[server_id], map)
            except Exception:
                await interaction.edit_original_message(
                    "Unable to detect the current gamemode. The whitelist on the server is not associated with a gamemode."
                )
                return

            with Client(
                reservations[server_id]["server"]["ip"],
                int(reservations[server_id]["server"]["port"]),
                passwd=reservations[server_id]["rcon"],
            ) as client:
                client.run(command)

            await interaction.edit_original_message(
                content="Changing map to " + map + ".", view=None
            )
