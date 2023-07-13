"""Files containing the server cog with commands for reserving/managing servers."""
import json
import string
import random
from typing import List

import aiohttp
import nextcord
from bs4 import BeautifulSoup
from nextcord.ext import tasks, commands, application_checks
from rcon.source import Client

import database
import util
from constants import VERSION
from servers.serveme_api import ServemeAPI
from servers import Reservation, Servers, ServerButton


with open("maps.json", encoding="UTF-8") as json_file:
    maps: dict = json.load(json_file)
    SIXES_MAPS: dict = maps["sixes"]
    HL_MAPS: dict = maps["hl"]


class ServerCog(commands.Cog):
    """A cog that holds all the commands for reserving/managing servers.

    Attributes:
        bot (nextcord.Client): The bot client.
    """

    def __init__(self, bot: nextcord.Client):
        self.servers: List[Reservation] = []
        self.bot = bot
        self.map_updater.start()  # pylint: disable=no-member
        self.server_status.start()  # pylint: disable=no-member

    @tasks.loop(hours=4)
    async def map_updater(self):
        """Updates the map pool for the bot, grabbing the latest from the RGL website."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://docs.rgl.gg/league/references/maps_and_configs/"
            ) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                map_marker = soup.find(id="custom-map-downloads")
                sixes_list = map_marker.find_next_sibling("ul")
                hl_list = sixes_list.find_next_sibling("ul")

                for tf_map in sixes_list.find_all("li"):
                    SIXES_MAPS[tf_map.text.rsplit("_", 1)[0]] = tf_map.text

                for tf_map in hl_list.find_all("li"):
                    if "/" in tf_map.text:
                        versions = tf_map.text.split(" / ", 1)
                        for map_version in versions:
                            HL_MAPS[map_version.strip()] = map_version.strip()
                        continue
                    HL_MAPS[tf_map.text.rsplit("_", 1)[0]] = tf_map.text

        print("Updated maps:\n" + str(SIXES_MAPS) + "\n" + str(HL_MAPS))

        map_dict = {"sixes": SIXES_MAPS, "hl": HL_MAPS}

        map_json = json.dumps(map_dict)

        with open("maps.json", "w", encoding="UTF-8") as outfile:
            outfile.write(map_json)

        await self.bot.sync_all_application_commands(update_known=True)
        print("All app commands synced")

    @commands.Cog.listener("on_application_command_error")
    async def handle_errors(self, interaction: nextcord.Interaction, error: Exception):
        """Handles errors that occur when using slash commands."""
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

    @nextcord.slash_command(
        name="reserve", description="Reserve a new server on na.serveme.tf."
    )
    @util.is_setup()
    @util.is_runner()
    async def reserve_server(
        self,
        interaction: nextcord.Interaction,
        tf_map: str = nextcord.SlashOption(
            name="map",
            description="The map to set on the server.",
            choices=maps["sixes"] | maps["hl"],
        ),
        gamemode: str = nextcord.SlashOption(
            name="gamemode",
            description="The gamemode config to set on the server.",
            choices={
                "6s": "sixes",
                "HL": "highlander",
            },
        ),
        whitelist: int = nextcord.SlashOption(
            name="whitelist",
            description="The whitelist to set on the server.",
            choices={
                "RGL 6s": 13531,
                "RGL HL": 13397,
                "RGL NR6s": 9914,
                "TF2CC Regular": 13797,
                "TF2CC Newbie": 13798,
            },
        ),
    ):
        """Reserves a server for the user to use.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
            tf_map (str): The map to set on the server
            gamemode (str): The gamemode config to set on the server
        """
        await interaction.response.defer()
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        servers, times = await ServemeAPI().get_new_reservation(serveme_api_key)

        reserve: dict
        server_found: bool = False

        for server in servers["servers"]:
            if "chi" in server["ip"]:
                if 536 != server["id"]:
                    print("New server reserved: " + str(server))
                    reserve = server
                    server_found = True
                    break

        if not server_found:
            for server in servers["servers"]:
                if "ks" in server["ip"]:
                    print("New server reserved: " + str(server))
                    reserve = server
                    server_found = True
                    break

        connect_password = "pug." + "".join(
            random.choices(string.ascii_letters + string.digits, k=8)
        )
        rcon_password = "rcon.pug." + "".join(
            random.choices(string.ascii_letters + string.digits, k=20)
        )

        if gamemode == "sixes":
            if tf_map not in maps["sixes"].values():
                await interaction.send("Invalid map.")
                return
            if tf_map.startswith("cp_"):
                server_config_id = 69  # rgl_6s_5cp_scrim
            else:
                server_config_id = 68  # rgl_6s_koth_bo5
        else:
            if tf_map not in maps["hl"].values():
                await interaction.send("Invalid map.")
                return
            if tf_map.startswith("pl_"):
                server_config_id = 55
            else:
                server_config_id = 54

        reserve_string = {
            "reservation": {
                "starts_at": times["reservation"]["starts_at"],
                "ends_at": times["reservation"]["ends_at"],
                "rcon": rcon_password,
                "password": connect_password,
                "server_id": reserve["id"],
                "enable_plugins": True,
                "enable_demos_tf": True,
                "first_map": tf_map,
                "server_config_id": server_config_id,
                "whitelist_id": None,
                "custom_whitelist_id": whitelist,
                "auto_end": True,
            }
        }

        reserve_json = json.dumps(reserve_string)

        server_id: int
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://na.serveme.tf/api/reservations?api_key=" + serveme_api_key,
                data=reserve_json,
                headers={"Content-type": "application/json"},
            ) as resp:
                server_data = await resp.json()
                server_id = server_data["reservation"]["id"]
                print(await resp.text())

        connect = (
            "connect "
            + reserve["ip_and_port"]
            + '; password "'
            + connect_password
            + '"'
        )
        rcon = (
            "rcon_address "
            + reserve["ip_and_port"]
            + '; rcon_password "'
            + rcon_password
            + '"'
        )
        connect_link = (
            "steam://connect/" + reserve["ip_and_port"] + "/" + connect_password
        )

        tf_oog_pw_link = (
            f"https://tf.oog.pw/connect/{reserve['ip_and_port']}/{connect_password}"
        )

        embed = nextcord.Embed(title="Server started!", color=0xF0984D)
        embed.add_field(name="Server", value=reserve["name"], inline=False)
        embed.add_field(name="Connect", value=connect, inline=False)
        embed.add_field(
            name="RCON", value="RCON has been sent in the rcon channel.", inline=False
        )
        embed.add_field(name="Map", value=tf_map, inline=False)
        embed.set_footer(text=VERSION)
        reserve_msg = await interaction.send(embed=embed)

        # RCON Message
        rcon_channel = self.bot.get_channel(guild_data["rcon"])
        rcon_msg = await rcon_channel.send(rcon)

        # Connect Message
        connect_embed = nextcord.Embed(
            title=tf_oog_pw_link, url=tf_oog_pw_link, color=0x3DFF1F
        )
        connect_embed.add_field(name="Command", value=connect, inline=False)
        connect_embed.add_field(name="Connect Link", value=connect_link, inline=False)
        connect_channel: nextcord.TextChannel
        if interaction.guild_id == 727627956058325052:  # TF2CC
            if whitelist == 13797:  # Normal whitelist
                connect_channel = self.bot.get_channel(934275639291310121)
            elif whitelist == 13798:  # Newbie whitelist
                connect_channel = self.bot.get_channel(958053551073021972)
            else:
                connect_channel = self.bot.get_channel(guild_data["connect"])
        else:
            connect_channel = self.bot.get_channel(guild_data["connect"])

        connect_msg = await connect_channel.send(embed=connect_embed)

        self.servers.append(
            Reservation(
                server_id, serveme_api_key, [reserve_msg, rcon_msg, connect_msg]
            )
        )

    @util.is_setup()
    @util.is_runner()
    @nextcord.slash_command(name="map", description="Change the map on a reservation.")
    async def change_map(
        self,
        interaction: nextcord.Interaction,
        tf_map: str = nextcord.SlashOption(
            name="map",
            choices=maps["sixes"] | maps["hl"],
        ),
    ):
        """Changes the map on a user's reserved server.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
            tf_map (str): The map to set on the server
        """
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = await ServemeAPI().get_current_reservations(serveme_api_key)

        if len(reservations) == 0:
            await interaction.send(
                "There are no active reservations with the associated serveme account."
            )
            return
        if len(reservations) == 1:
            try:
                command: str = await util.get_exec_command(reservations[0], tf_map)
            except Exception:
                await interaction.send(
                    """Unable to detect the current gamemode.
                    The whitelist on the server is not associated with a gamemode."""
                )
                return

            with Client(
                reservations[0]["server"]["ip"],
                int(reservations[0]["server"]["port"]),
                passwd=reservations[0]["rcon"],
            ) as client:
                client.run(command)

            await interaction.send("Changing map to `" + tf_map + "`.")
            return

        server_view = Servers()

        for num, reservation in enumerate(reservations):
            button = ServerButton(reservation, num)
            server_view.add_item(button)

        await interaction.send(
            "Select a reservation to change the map on.",
            view=server_view,
            ephemeral=True,
        )
        await server_view.wait()
        server_id = server_view.server_chosen

        try:
            exec_command: str = await util.get_exec_command(
                reservations[server_id], tf_map
            )
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
            client.run(exec_command)

        await interaction.edit_original_message(
            content="Changing map to `" + tf_map + "`.", view=None
        )

    @util.is_setup()
    @util.is_runner()
    @nextcord.slash_command(
        name="rcon", description="Send an rcon command to a reservation."
    )
    async def rcon_command(self, interaction: nextcord.Interaction, command: str):
        """Run a rcon command on one of the user's reserved servers.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
            command (str): The command to run on the TF2 server.
        """
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = await ServemeAPI().get_current_reservations(serveme_api_key)

        if len(reservations) == 0:
            await interaction.send(
                "There are no active reservations with the associated serveme account."
            )
            return
        if len(reservations) == 1:
            with Client(
                reservations[0]["server"]["ip"],
                int(reservations[0]["server"]["port"]),
                passwd=reservations[0]["rcon"],
            ) as client:
                client.run(command)
            await interaction.send("Ran command `" + command + "`")
        else:
            server_view = Servers()

            for num, reservation in enumerate(reservations):
                button = ServerButton(reservation, num)
                server_view.add_item(button)

            await interaction.send(
                "Select a reservation to run the command on.", view=server_view
            )
            await server_view.wait()
            server_id = server_view.server_chosen

            with Client(
                reservations[server_id]["server"]["ip"],
                int(reservations[server_id]["server"]["port"]),
                passwd=reservations[server_id]["rcon"],
            ) as client:
                client.run(command)

            await interaction.edit_original_message(
                content="Ran command `" + command + "`", view=None
            )

    @util.is_setup()
    @util.is_runner()
    @nextcord.slash_command(name="end", description="End a reservation.")
    async def end_reservation(self, interaction: nextcord.Interaction):
        """End a reservation.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
        """
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = await ServemeAPI().get_current_reservations(serveme_api_key)

        async with aiohttp.ClientSession() as session:
            if len(reservations) == 0:
                await interaction.send(
                    "There are no active reservations with the associated serveme account."
                )
                return
            if len(reservations) == 1:
                async with session.delete(
                    f"https://na.serveme.tf/api/reservations/{reservations[0]['id']}?api_key={serveme_api_key}",
                ) as resp:
                    if resp.status == 200:
                        await interaction.send(
                            f"Ending reservation `#{reservations[0]['id']}`."
                        )
                    else:
                        await interaction.send(
                            f"Failed to end reservation `#{reservations[0]['id']}`.\nStatus code: {resp.status}"
                        )
            else:
                server_view = Servers()

                for num, reservation in enumerate(reservations):
                    button = ServerButton(reservation, num)
                    server_view.add_item(button)

                await interaction.send("Select a reservation to end.", view=server_view)
                await server_view.wait()
                server_id = server_view.server_chosen

                async with session.delete(
                    f"https://na.serveme.tf/api/reservations/{reservations[server_id]['id']}?api_key={serveme_api_key}",
                ) as resp:
                    if resp.status == 200:
                        await interaction.edit_original_message(
                            content=f"Ending reservation `#{reservations[server_id]['id']}`.",
                            view=None,
                        )
                    else:
                        await interaction.edit_original_message(
                            content=f"Failed to end reservation `#{reservations[server_id]['id']}`.\nStatus code: {resp.status}",
                            view=None,
                        )

    @tasks.loop(minutes=1)
    async def server_status(self):
        """Update the status of the servers every minute."""
        for server in self.servers:
            status: bool = await server.is_active()
            if not status:
                for message in server.messages:
                    try:
                        await message.delete()
                    except nextcord.HTTPException:
                        self.servers.remove(server)
                        continue
                self.servers.remove(server)
        return

    @server_status.error
    async def error_handler(self, exception: Exception):
        """Handles printing errors to console for the loop

        Args:
            exception (Exception): The exception that was raised
        """
        print("Error in server_status loop:\n")
        print(exception.__class__.__name__)
        print(exception)
