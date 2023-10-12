"""Files containing the server cog with commands for reserving/managing servers."""
import json
import re
import string
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import aiohttp
import nextcord
import pytz
from bs4 import BeautifulSoup
from nextcord.ext import tasks, commands, application_checks
from rcon.source import Client

import database
import util
from constants import VERSION
from servers.serveme_api import ServemeAPI  # disable=attr-defined
from servers import Reservation, Servers, ServerButton, MapSelection


with open("maps.json", encoding="UTF-8") as json_file:
    maps: dict = json.load(json_file)
    SIXES_MAPS: dict = maps["sixes"]
    HL_MAPS: dict = maps["hl"]

PT_MAPS: dict = {
    "pass_arena2": "pass_arena2_b8",
    "pass_stadium": "pass_stadium_b31",
    "pass_stonework": "pass_stonework_a24",
}


class ServerCog(commands.Cog):
    """A cog that holds all the commands for reserving/managing servers.

    Attributes:
        bot (nextcord.Client): The bot client.
    """

    def __init__(self, bot: nextcord.Client):
        self.servers: List[Reservation] = []
        self.bot = bot
        self.all_maps: list = []
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

        # Handle the FastDL all map pool
        self.all_maps = await ServemeAPI.fetch_all_maps(False)

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
    async def reserve(
        self,
        interaction: nextcord.Interaction,
        tf_map: str = nextcord.SlashOption(
            name="map",
            description="The map to set on the server. The bot will automatically find and use the newest version.",
        ),
        gamemode: str = nextcord.SlashOption(
            name="gamemode",
            description="The gamemode config to set on the server.",
            choices={
                "6s": "sixes",
                "Highlander": "highlander",
                "Passtime": "passtime",
                "None": "none",
            },
        ),
        whitelist: Optional[int] = nextcord.SlashOption(
            name="whitelist",
            description="The whitelist to set on the server.",
            default=None,
            choices={
                "RGL 6s": 13531,
                "RGL HL": 13397,
                "RGL NR6s": 9914,
                "TF2CC Regular": 13797,
                "TF2CC Newbie": 13798,
            },
        ),
        start_time: Optional[str] = nextcord.SlashOption(
            name="start_time",
            description="Start time in the format HH:MM (24 hour clock)",
            default=None,
            max_length=5,
            min_length=4,
            required=False,
        ),
        duration: float = nextcord.SlashOption(
            name="duration",
            description="How long to reserve the server (between 2 to 5 hours)",
            default=2,
            min_value=2,
            max_value=5,
            required=False,
        ),
        tzone: Optional[int] = nextcord.SlashOption(
            name="utc_time_zone",
            description="The UTC offset for the timezone of the optional start time (default US/Eastern)",
            default=None,
            min_value=-12,
            max_value=14,
            required=False,
        ),
    ):
        """Reserves a server for the user to use.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
            tf_map (str): The map to set on the server
            gamemode (str): The gamemode config to set on the server
            whitelist (str): The whitelist to set on the server
            start_time (str): The start time of the reservation
            duration (int): The duration of the reservation
            tzone (int): The UTC offset of the timezone to use
        """
        await interaction.response.defer()

        dt_start: datetime
        if not tzone:
            # Get default timezone adjusted for daylight savings
            ept = pytz.timezone("US/Eastern")
            dt_start = datetime.now().astimezone(ept)
        else:
            dt_start = datetime.now(tz=timezone(timedelta(hours=tzone)))

        if start_time:
            try:
                # Ensure correct format and valid time
                match = re.match(
                    r"[0-9]{1,2}:[0-9]{2}",
                    start_time,
                )
                if not match:
                    raise ValueError("Must be in HH:MM format")

                # Adjust datetime object to inputted start time
                split_time = start_time.split(":")
                hours = int(split_time[0])
                mins = int(split_time[1])

                if 0 > hours or hours > 24:
                    raise ValueError("Hours must be between 0 and 23")
                if 0 > mins or mins > 59:
                    raise ValueError("Minutes must be between 0 and 59")

                # Can't reserve a server in the past! Move to tomorrow
                if dt_start.hour > hours:
                    dt_start += timedelta(days=1)

                dt_start -= timedelta(hours=dt_start.hour, minutes=dt_start.minute)
                dt_start += timedelta(hours=hours, minutes=mins)
            except ValueError as err:
                await interaction.send(f"Start time input error: {err}", ephemeral=True)
                return

        map_versions = await ServemeAPI.fetch_newest_version(
            tf_map
        )  # pylint: disable=no-member
        print(map_versions)
        if map_versions is None:
            await interaction.send(
                f"Invalid map error: Not able to find any map that starts with {tf_map}",
                ephemeral=True,
            )
            return
        if isinstance(map_versions, str):
            chosen_map = map_versions
        else:
            map_selector_view = MapSelection(map_versions)
            await interaction.send(
                "Multiple map versions were found. Please select the right version.",
                view=map_selector_view,
            )
            status = await map_selector_view.wait()
            if status:
                return
            chosen_map = map_selector_view.map_chosen

        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        servers, times = await ServemeAPI().get_new_reservation(
            serveme_api_key, dt_start, duration
        )

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
            whitelist_id = 20  # 6s whitelist ID
            if tf_map not in maps["sixes"].values():
                await interaction.send("Invalid map.")
                return
            if tf_map.startswith("cp_"):
                server_config_id = 69  # rgl_6s_5cp_scrim
            else:
                server_config_id = 68  # rgl_6s_koth_bo5
        elif gamemode == "highlander":
            whitelist_id = 22  # HL whitelist ID
            if tf_map not in maps["hl"].values():
                await interaction.send("Invalid map.")
                return
            if tf_map.startswith("pl_"):
                server_config_id = 55
            else:
                server_config_id = 54
        elif gamemode == "passtime":
            whitelist_id = 26  # PT whitelist ID
            server_config_id = 116  # RGL PT_Push config ID in serveme
        elif gamemode == "none":
            whitelist_id = None
            server_config_id = None

        # Fix custom whitelists not working
        if whitelist in (13798, 13797):
            whitelist_id = None  # type: ignore

        reserve_string = {
            "reservation": {
                "starts_at": times["reservation"]["starts_at"],
                "ends_at": times["reservation"]["ends_at"],
                "rcon": rcon_password,
                "password": connect_password,
                "server_id": reserve["id"],
                "enable_plugins": True,
                "enable_demos_tf": True,
                "first_map": chosen_map,
                "server_config_id": server_config_id,
                "whitelist_id": whitelist_id,
                "custom_whitelist_id": whitelist,
                "auto_end": True,
            }
        }

        print(reserve_string)
        reserve_json = json.dumps(reserve_string)

        server_id: int
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://na.serveme.tf/api/reservations?api_key=" + serveme_api_key,
                data=reserve_json,
                headers={"Content-type": "application/json"},
            ) as resp:
                server_data = await resp.json()
                print(server_data)
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
            f"https://pugBot.tf/connect/{reserve['ip_and_port']}/{connect_password}"
        )

        embed = nextcord.Embed(title="Server reserved!", color=0xF0984D)
        embed.add_field(
            name="Server", value=f"{reserve['name']} - #{server_id}", inline=False
        )
        start = datetime.fromisoformat(server_data["reservation"]["starts_at"])
        embed.add_field(
            name="Start Time",
            value=f"<t:{int(start.timestamp())}:t>",
            inline=True,
        )
        end = datetime.fromisoformat(server_data["reservation"]["ends_at"])
        embed.add_field(
            name="End Time",
            value=f"<t:{int(end.timestamp())}:t>",
            inline=True,
        )
        embed.add_field(name="Connect", value=connect, inline=False)

        # RCON message
        rcon_channel = self.bot.get_channel(guild_data["rcon"])
        if rcon_channel == interaction.channel:
            # Include RCON in this embed if we are already in the RCON channel
            embed.add_field(name="RCON", value=rcon, inline=False)
        else:
            await rcon_channel.send(rcon)

        embed.add_field(name="Map", value=chosen_map, inline=False)
        embed.set_footer(text=VERSION)
        reserve_msg = await interaction.edit_original_message(
            content=None, embed=embed, view=None
        )

        # Connect Message
        connect_embed = nextcord.Embed(
            title=tf_oog_pw_link, url=tf_oog_pw_link, color=0x3DFF1F
        )
        connect_embed.add_field(
            name="Server", value=f"{reserve['name']} - #{server_id}", inline=False
        )
        connect_embed.add_field(name="Command", value=connect, inline=False)
        connect_embed.add_field(name="Connect Link", value=connect_link, inline=False)

        if interaction.guild_id == 727627956058325052:  # TF2CC
            if interaction.user.voice is not None:
                category = interaction.user.voice.channel.category

                for channel in category.channels:
                    if "connect" in channel.name:
                        connect_channel = channel
                        break
            else:
                connect_channel = self.bot.get_channel(guild_data["connect"])
        else:
            connect_channel = self.bot.get_channel(guild_data["connect"])

        connect_msg = await connect_channel.send(embed=connect_embed)

        self.servers.append(
            Reservation(server_id, serveme_api_key, [reserve_msg, connect_msg])
        )

    @util.is_setup()
    @util.is_runner()
    @nextcord.slash_command(name="map", description="Change the map on a reservation.")
    async def change_map(
        self,
        interaction: nextcord.Interaction,
        tf_map: str = nextcord.SlashOption(
            name="map",
            description="The map to change to. The bot will automatically find and use the newest version.",
        ),
    ):
        """Changes the map on a user's reserved server.

        Args:
            interaction (nextcord.Interaction): Interaction object from invoking the command.
            tf_map (str): The map to set on the server
        """
        await interaction.response.defer()
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = (await ServemeAPI().get_current_reservations(serveme_api_key))[0]

        if len(reservations) == 0:
            await interaction.send(
                "There are no active reservations with the associated serveme account."
            )
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

        map_versions = await ServemeAPI.fetch_newest_version(
            tf_map
        )  # pylint: disable=no-member
        print(map_versions)
        if map_versions is None:
            await interaction.edit_original_message(
                content=f"Invalid map error: Not able to find any map that starts with {tf_map}",
                view=None,
            )
            return
        if isinstance(map_versions, str):
            chosen_map = map_versions
        else:
            map_selector_view = MapSelection(map_versions)
            await interaction.edit_original_message(
                content="Multiple map versions were found. Please select the right version.",
                view=map_selector_view,
            )
            status = await map_selector_view.wait()
            if status:
                return
            chosen_map = map_selector_view.map_chosen

        try:
            exec_command: str = await util.get_exec_command(
                reservations[server_id], chosen_map
            )
        except Exception:
            await interaction.edit_original_message(
                content="Unable to detect the current gamemode. The whitelist on the server is not associated with a gamemode."
            )
            return

        with Client(
            reservations[server_id]["server"]["ip"],
            int(reservations[server_id]["server"]["port"]),
            passwd=reservations[server_id]["rcon"],
        ) as client:
            client.run(exec_command)

        await interaction.edit_original_message(
            content="Changing map to `" + chosen_map + "`.", view=None
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
        await interaction.response.defer()
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        reservations = (await ServemeAPI().get_current_reservations(serveme_api_key))[0]

        if len(reservations) == 0:
            await interaction.send(
                "There are no active reservations with the associated serveme account."
            )
            return

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
        await interaction.response.defer()
        guild_data = database.get_server(interaction.guild.id)
        serveme_api_key = guild_data["serveme"]
        (
            current_reservations,
            future_reservations,
        ) = await ServemeAPI().get_current_reservations(serveme_api_key)
        reservations = current_reservations + future_reservations

        async with aiohttp.ClientSession() as session:
            if len(reservations) == 0:
                await interaction.send(
                    "There are no active reservations with the associated serveme account."
                )
                return

            server_view = Servers()

            for num, reservation in enumerate(current_reservations):
                button = ServerButton(reservation, num, True)
                server_view.add_item(button)

            for num, reservation in enumerate(future_reservations):
                button = ServerButton(
                    reservation, num + len(current_reservations), False
                )
                server_view.add_item(button)

            await interaction.send("Select a reservation to end.", view=server_view)
            status = await server_view.wait()
            if status:
                return
            server_id = server_view.server_chosen

            async with session.delete(
                f"https://na.serveme.tf/api/reservations/{reservations[server_id]['id']}?api_key={serveme_api_key}",
            ) as resp:
                if resp.status == 200:
                    await interaction.edit_original_message(
                        content=f"Ending reservation `#{reservations[server_id]['id']}`.",
                        view=None,
                    )
                elif resp.status == 204:
                    await interaction.edit_original_message(
                        content=f"Canceling future reservation `#{reservations[server_id]['id']}`.",
                        view=None,
                    )
                else:
                    await interaction.edit_original_message(
                        content=f"Failed to end reservation `#{reservations[server_id]['id']}`.\nStatus code: {resp.status}",
                        view=None,
                    )

    @reserve.on_autocomplete("tf_map")
    @change_map.on_autocomplete("tf_map")
    async def map_autocomplete(self, interaction: nextcord.Interaction, map_query: str):
        """Autocompletes the map name for the user.

        Args:
            interaction (nextcord.Interaction): Interaction to respond to
            map_query (str): The map name to autocomplete
        """
        if len(map_query.split("_")) > 1:
            map_search = await ServemeAPI.fetch_newest_version(
                map_query, maps_list=self.all_maps
            )
            print(map_search)
            if map_search is None:
                await interaction.response.send_autocomplete(["No results."])
                return
            if isinstance(map_search, str):
                await interaction.response.send_autocomplete([map_search])
                return
            if len(map_search) > 25:
                await interaction.response.send_autocomplete(
                    ["Too many results. Please narrow your search."]
                )
                return
            await interaction.response.send_autocomplete(map_search)
            return

        await interaction.response.send_autocomplete(
            ["Please type the beginning of the map name to get autocomplete results."]
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
                        try:
                            self.servers.remove(server)
                        except ValueError:
                            print("Server not in list")
                            print(self.servers)
                            continue
                        continue
                try:
                    self.servers.remove(server)
                except ValueError:
                    print("Server not in list")
                    print(self.servers)
                    continue
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
