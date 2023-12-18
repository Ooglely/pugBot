"""Contains the webserver cog, which is responsible for the webserver and registering users."""
import asyncio
import nextcord
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel  # pylint: disable=no-name-in-module

import util
from constants import API_PASSWORD, BOT_COLOR, PORT, DEV_REGISTRATIONS, DEV_DISCORD_LINK
from database import (
    add_player,
    get_all_servers,
    update_divisons,
    get_player_from_steam,
    get_player_from_discord,
)
from registration.update_roles import load_guild_settings
from rglapi import RglApi

app: FastAPI = FastAPI()
RGL: RglApi = RglApi()


class NewUser(BaseModel):
    """Pydantic model for a new user from the website

    Attributes:
        steam (str): The user's steam ID
        discord (str): The user's discord ID
    """

    steam: str
    discord: str


class NewConnect(BaseModel):
    """Pydantic model for a new connect command from the TF2 server

    Attributes:
        discordID (str): The discord ID to send the connect command to
        connectCommand (str): The connect command to send to the user
    """

    discordID: str
    connectCommand: str


class WebserverCog(nextcord.ext.commands.Cog):
    """Cog that stores all the functions to register users."""

    def __init__(self, bot):
        self.bot: nextcord.Client = bot
        asyncio.create_task(self.start_server())

    @nextcord.slash_command(
        name="register",
        description="Manually register a user in the database.",
    )
    @util.is_runner()
    async def manual_registration(
        self,
        interaction: nextcord.Interaction,
        discord_user: nextcord.User,
        steam_id: str,
    ):
        """Manually registers a user into the bot's database.

        Args:
            interaction (nextcord.Interaction): The discord interaction
            discord_user (nextcord.User): The discord user to register
            steam_id (str): The steam id/link of the user to register
        """
        await interaction.response.defer()
        result = await self.register_new_user(
            int(discord_user.id), int(util.get_steam64(steam_id))
        )
        if not result:
            # Registration succeeded
            add_player(str(util.get_steam64(steam_id)), str(discord_user.id))
            await interaction.send(
                f"User registered.\nSteam: `{util.get_steam64(steam_id)}`\nDiscord: `{discord_user.id}`",
                ephemeral=True,
            )
        else:
            # Registration failed
            await interaction.send(
                f"Error occurred while manually registering user: {result}`",
                ephemeral=True,
            )

    async def register_new_user(self, discord_id: int, steam_id: int):
        """Goes through the checks and registers a new user in the database.

        Checks in order are:
        1. Amount of logs from logs.tf
        2. Registered in RGL
        3. Played on at least 1 RGL team
        4. Not RGL banned
        5. Highest division played

        Args:
            discord_id (int): Discord ID of the player
            steam_id (int): Steam ID of the player
        """

        user = self.bot.get_user(discord_id)

        try:
            get_player_from_steam(steam_id)
            return f"Steam profile is already linked. Please contact PugBot devs {DEV_DISCORD_LINK}"
        except LookupError:
            # pass is not a mistake or incomplete implementation, this means the steam is unique and we can proceed
            pass

        try:
            get_player_from_discord(discord_id)
            return f"Discord is already linked. Please contact PugBot devs {DEV_DISCORD_LINK}"
        except LookupError:
            # pass is not a mistake or incomplete implementation, this means the steam is unique and we can proceed
            pass

        # If the user doesn't have an RGL profile, don't bother registering
        try:
            player_data = await RGL.get_player(steam_id)
        except LookupError:
            return "RGL profile does not exist. Please create one at https://rgl.gg/?showFront=true and try again."

        # Gather player data and
        player_divs = await RGL.get_div_data(steam_id)
        current_ban = await RGL.check_banned(steam_id)
        log_num = await util.get_total_logs(str(steam_id))

        await update_divisons(steam_id, player_divs)
        print(player_divs)

        # Build the string for the checks field
        checks_field = ""

        # Log check
        if log_num >= 50:
            checks_field += "✅ Logs: " + str(log_num)
        else:
            checks_field += "❌ Logs: " + str(log_num)

        checks_field += "\n✅ RGL Profile exists"

        team_history = 0
        for temp in player_divs.values():
            for result in temp.values():
                team_history += result
        # Check if they have been on a team.
        if team_history <= 0:
            checks_field += "\n❌ No RGL team history"
        else:
            checks_field += "\n✅ RGL team history exists"

        # Check if they are banned.
        if current_ban:
            checks_field += "\n❌ Currently banned from RGL"
        else:
            checks_field += "\n✅ Not banned from RGL"

        # Set up an embed to send to this guild's registrations channel
        registration_embed = nextcord.Embed(
            title="New Registration",
            description=player_data["name"],
            url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
            color=BOT_COLOR,
        )
        registration_embed.add_field(
            name="Discord", value=f"<@{discord_id}>\n@{user.name}", inline=True
        )
        registration_embed.add_field(name="Steam", value=str(steam_id), inline=True)
        registration_embed.set_thumbnail(url=player_data["avatar"])

        # output the results to the dev guild
        registration_embed.add_field(name="Checks", value=checks_field, inline=False)
        await self.bot.get_channel(DEV_REGISTRATIONS).send(embed=registration_embed)

        # Remove the last field in preparation the guild embeds
        registration_embed.remove_field(-1)

        all_servers = get_all_servers()
        for server in all_servers:
            # If registration settings are not set up, skip
            if "registration" not in server:
                continue
            # If registration is disabled, skip
            if not server["registration"]["enabled"]:
                continue

            # Load this guild's settings, roles, and channels from the DB
            loaded = load_guild_settings(self.bot, server["guild"])
            if loaded is None:
                continue

            # If member is not in server, skip
            member = loaded["guild"].get_member(discord_id)
            if member is None:
                continue

            # If the bypass role exists and the user has it, skip
            bypass_role = loaded["roles"]["bypass"]
            if bypass_role:
                if member.get_role(bypass_role) is not None:
                    continue

            game_mode = loaded["settings"]["gamemode"]
            mode = loaded["settings"]["mode"]
            division = player_divs[game_mode][mode]

            division = max(division, 0)

            # Get the division role or, if banned and setting is to follow RGL bans, get the ban role
            role_to_give = loaded["roles"]["divisions"][division]
            if current_ban and loaded["settings"]["ban"]:
                role_to_give = loaded["roles"]["rgl_ban"]

            # Lastly, add the role and output the results to the guild
            await member.add_roles(role_to_give)
            registration_embed.add_field(
                name="Roles Added",
                value=f"<@&{role_to_give.id}>",
                inline=False,
            )
            registration_embed.add_field(
                name="Checks", value=checks_field, inline=False
            )
            await loaded["channels"]["registration"].send(embed=registration_embed)

            # Remove the last 2 fields in preparation for the next guild
            registration_embed.remove_field(-1)
            registration_embed.remove_field(-1)

    async def send_connect_dm(self, discord_id: int, connect_command: str):
        """Sends a DM to the intended user with the connect commmand.

        This is for use with my gamemode menu TF2 server plugin.

        Args:
            discordID (int): The discord ID to send the DM to
            connectCommand (str): The command to send
        """
        connect_embed = nextcord.Embed(
            title="New Connect",
            color=0xF0984D,
        )
        connect_embed.add_field(name="Connect Command", value=connect_command)
        await self.bot.get_user(int(discord_id)).send(embed=connect_embed)

    async def start_server(self: nextcord.ext.commands.Cog):
        """Starts the uvicorn webserver with the correct config."""
        config = uvicorn.Config(
            "registration.webserver:app",
            host="0.0.0.0",
            port=PORT,
            log_level="info",
        )
        server = uvicorn.Server(config)
        app.cog = self
        await server.serve()


@app.get("/")
async def hello_world():
    """A test to make sure that the webserver is up and working."""
    return {"message": "Hello world"}


@app.post("/api/register")
async def register(registration: NewUser, request: Request):
    """Starts the registration process for a new user.

    Args:
        registration (NewUser): The steam and discord ID of the user
        request (Request): The request to check for the API password in the header

    Returns:
        dict: Describes success or errors
    """
    print(registration)
    if "password" in request.headers:
        if request.headers["password"] == API_PASSWORD:
            print(registration.steam)
            print(registration.discord)
            await asyncio.sleep(3)
            result = await app.cog.register_new_user(  # pylint: disable=no-member
                int(registration.discord), int(registration.steam)
            )
            if result:
                user = app.cog.bot.get_user(  # pylint: disable=no-member
                    int(registration)
                )
                await user.send(content=f"Registration failed: Your {result}")

            return {"message": "Success"}
        return {"message": "Wrong password"}
    print("Incorrect password in headers")
    print(request.headers)


@app.post("/api/send_connect")
async def send_connect(connect: NewConnect, request: Request):
    """Runs the send_connect_dm from the bot using a request with connect info

    Args:
        connect (NewConnect): The connect command
        request (Request): The request to check for the plugin in headers

    Returns:
        dict: Describes success or errors
    """
    print(connect)
    if request.headers["user-agent"].startswith("sm-ripext"):
        print(connect.discordID)
        print(connect.connectCommand)
        await app.cog.send_connect_dm(  # pylint: disable=no-member
            int(connect.discordID), str(connect.connectCommand)
        )
        return {"message": "Success"}

    print("Request not from TF2 plugin")
    print(request.headers)
    return {"message": "Wrong password"}
