"""Contains the webserver cog, which is responsible for the webserver and registering users."""
import asyncio
import nextcord
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel  # pylint: disable=no-name-in-module

import util
from constants import API_PASSWORD, BOT_COLOR, PORT
from database import add_player, get_all_servers, update_divisons
from registration import RegistrationSettings
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
    """Cog that stores all of the functions to register users."""

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
        await self.register_new_user(
            int(discord_user.id), int(util.get_steam64(steam_id))
        )
        add_player(str(util.get_steam64(steam_id)), str(discord_user.id))
        await interaction.send(
            f"User registered.\nSteam: `{util.get_steam64(steam_id)}`\nDiscord: `{discord_user.id}`",
            ephemeral=True,
        )

    async def register_new_user(self, discord_id: int, steam_id: int):
        """Goes through the checks and registers a new user in the database.

        Checks in order are:
        1. Amount of logs from logs.tf
        2. Registered in RGL
        3. Played on at least 1 RGL team
        4. Not RGL banned
        5. Highest divison played

        Args:
            discord_id (int): Discord ID of the player
            steam_id (int): Steam ID of the player
        """
        # If the user doesn't have an RGL profile, don't bother registering
        member = self.bot.get_user(discord_id)
        player_data = {}
        try:
            player_data = await RGL.get_player(steam_id)
        except LookupError:
            await member.send(
                content="Registration failed: Your RGL profile does not exist. Please create one at https://rgl.gg/?showFront=true and try again."
            )
            return
        await asyncio.sleep(2)
        player_divs = await RGL.get_div_data(steam_id)
        await update_divisons(steam_id, player_divs)
        print(player_divs)
        all_servers = get_all_servers()
        for server in all_servers:
            # If registration settings are not set up, skip
            if "registration" not in server:
                continue
            # If registration is disabled, skip
            if not server["registration"]["enabled"]:
                continue
            guild = self.bot.get_guild(server["guild"])
            # If guild is not found, skip
            if guild is None:
                continue
            # If member is not in server, skip
            if guild.get_member(discord_id) is None:
                continue
            reg_settings = RegistrationSettings()
            reg_settings.import_from_db(server["guild"])

            gamemode: str
            if reg_settings.gamemode == "sixes":
                gamemode = "sixes"
            elif reg_settings.gamemode == "highlander":
                gamemode = "hl"

            division = player_divs[gamemode][reg_settings.mode]

            no_exp_role: nextcord.Role = guild.get_role(reg_settings.roles["noexp"])
            nc_role: nextcord.Role = guild.get_role(reg_settings.roles["newcomer"])
            am_role: nextcord.Role = guild.get_role(reg_settings.roles["amateur"])
            im_role: nextcord.Role = guild.get_role(reg_settings.roles["intermediate"])
            main_role: nextcord.Role = guild.get_role(reg_settings.roles["main"])
            adv_role: nextcord.Role = guild.get_role(reg_settings.roles["advanced"])
            inv_role: nextcord.Role = guild.get_role(reg_settings.roles["invite"])
            ban_role: nextcord.Role = guild.get_role(reg_settings.roles["ban"])

            registration_channel: nextcord.TextChannel = guild.get_channel(
                reg_settings.channels["registration"]
            )

            player: nextcord.Member = guild.get_member(discord_id)

            if reg_settings.bypass:
                if reg_settings.roles["bypass"] is not None:
                    if player.get_role(reg_settings.roles["bypass"]) is not None:
                        continue

            # Setup an embed to send to the registrations channel:
            registration_embed = nextcord.Embed(
                title="New Registration",
                url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
                color=BOT_COLOR,
            )
            registration_embed.add_field(
                name="Discord", value=f"<@{discord_id}>", inline=True
            )
            registration_embed.add_field(name="Steam", value=str(steam_id), inline=True)

            # We will add a checks field later, but want to add data to it as we go along the process.
            checks_field = ""

            # Log check
            log_num = await util.get_total_logs(str(steam_id))
            if log_num >= 50:
                checks_field += "✅ Logs: " + str(log_num)
            else:
                checks_field += "❌ Logs: " + str(log_num)

            registration_embed.set_thumbnail(url=player_data["avatar"])
            checks_field += "\n✅ RGL Profile exists"

            # Check if they have been on a team.
            if division <= 0:
                checks_field += "\n❌ No RGL team history"
                await player.add_roles(no_exp_role)
                registration_embed.add_field(
                    name="Roles Added", value=f"<@&{no_exp_role.id}>", inline=False
                )
                registration_embed.add_field(
                    name="Checks", value=checks_field, inline=False
                )
                await registration_channel.send(embed=registration_embed)
                continue

            checks_field += "\n✅ RGL team history exists"

            await asyncio.sleep(5)  # Sleep for 5 seconds to avoid rate limiting

            # Check if they are banned.
            if await RGL.check_banned(steam_id):
                checks_field += "\n❌ Currently banned from RGL"
                if reg_settings.ban:
                    await player.add_roles(ban_role)
                    registration_embed.add_field(
                        name="Roles Added", value=f"<@&{ban_role.id}>", inline=False
                    )
                    registration_embed.add_field(
                        name="Checks", value=checks_field, inline=False
                    )
                    await registration_channel.send(embed=registration_embed)
                    continue

            checks_field += "\n✅ Not banned from RGL"

            # Lastly, add the division role.
            # This implementation is so ugly man but I don't even know how else to do it
            roles_to_add: list[nextcord.Role] = [
                no_exp_role,
                nc_role,
                am_role,
                im_role,
                main_role,
                adv_role,
                adv_role,
                inv_role,
            ]

            await player.add_roles(roles_to_add[division])
            registration_embed.add_field(
                name="Roles Added",
                value=f"<@&{roles_to_add[division].id}>",
                inline=False,
            )

            registration_embed.add_field(
                name="Checks", value=checks_field, inline=False
            )
            await registration_channel.send(embed=registration_embed)

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
        app.bot = self
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
            await app.bot.register_new_user(  # pylint: disable=no-member
                int(registration.discord), int(registration.steam)
            )
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
        await app.bot.send_connect_dm(  # pylint: disable=no-member
            int(connect.discordID), str(connect.connectCommand)
        )
        return {"message": "Success"}

    print("Request not from TF2 plugin")
    print(request.headers)
    return {"message": "Wrong password"}
