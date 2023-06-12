"""Contains the webserver cog, which is responsible for the webserver and registering users."""
import asyncio
import nextcord
import uvicorn
from fastapi import FastAPI, Request

import agg
import util
from agg.stats import get_total_logs
from constants import API_PASSWORD, PORT
from rgl_api import RGL_API

app: FastAPI = FastAPI()
RGL: RGL_API = RGL_API()


class WebserverCog(nextcord.ext.commands.Cog):
    """Cog that stores all of the functions to register users."""

    def __init__(self, bot):
        self.bot: nextcord.Client = bot
        asyncio.create_task(self.start_server())

    @nextcord.slash_command(
        name="register",
        description="Manually register a user in the database.",
        guild_ids=agg.AGG_SERVER_ID,
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
        await self.check_new_register_ping(
            int(discord_user.id), int(util.get_steam64(steam_id))
        )
        await interaction.send(
            f"""User registered.\nSteam: `{util.get_steam64(steam_id)}`\n
            Discord: `{discord_user.id}`""",
            ephemeral=True,
        )

    # @commands.command(pass_context=False)
    async def check_new_register_ping(self, discord_id: int, steam_id: int):
        """Checks if a new registered user has already been registered or not

        Args:
            discord_id (int): Discord id of the new register attempt
            steam_id (int): Steam id of the new register attempt
        """
        # Registered Role ID: 1059583976039252108
        new_regs_channel = self.bot.get_guild(952817189893865482).get_channel(
            1060014665129791528
        )
        user = self.bot.get_guild(952817189893865482).get_member(discord_id)
        # If user is not in the agg server...
        if user is None:
            await new_regs_channel.send(
                f"New registration not found in server: {discord_id}"
            )
            print("User not found in server")
            return "User not found in server"
        # If the user doesn't have the Registered role
        if user.get_role(1059583976039252108) is None:
            await self.register_new_user(discord_id, steam_id)

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
        agg_server: nextcord.Guild = self.bot.get_guild(agg.AGG_SERVER_ID[0])

        discord_user: nextcord.Member = agg_server.get_member(discord_id)

        div_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
            1060023899666002001
        )
        new_regs_channel: nextcord.TextChannel = agg_server.get_channel(
            1060014665129791528
        )
        registration_channel: nextcord.TextChannel = agg_server.get_channel(
            996607763159457812
        )

        nc_am_role: nextcord.Role = agg_server.get_role(992286429881303101)
        im_ma_role: nextcord.Role = agg_server.get_role(992281832437596180)
        ad_in_role: nextcord.Role = agg_server.get_role(1060021145212047391)
        hl_ban_role: nextcord.Role = agg_server.get_role(1060020104462606396)
        six_ban_role: nextcord.Role = agg_server.get_role(1060020133495578704)

        sixes_role: nextcord.Role = agg_server.get_role(997600373399359608)
        hl_role: nextcord.Role = agg_server.get_role(997600342306988112)

        registered_role: nextcord.Role = agg_server.get_role(1059583976039252108)

        # Give registered role
        await discord_user.add_roles(registered_role)

        # Setup an embed to send to the new-registrations channel:
        registration_embed = nextcord.Embed(
            title="New Registration",
            url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
            color=0xFFFFFF,
        )
        registration_embed.add_field(
            name="Discord", value=f"<@{discord_id}>", inline=True
        )
        registration_embed.add_field(name="Steam", value=str(steam_id), inline=True)

        # We will add a checks field later, but want to add data to it as we go along the process.
        checks_field = ""

        # Since we have started the registration process we can delete
        # the messages the user has sent in #pug-registration
        # (if they have anyways)
        async for message in registration_channel.history(limit=100):
            if message.author.id == discord_id:
                await message.delete()

        # We want to check some things to allow a player in automatically:
        # 1. They have at least 50 logs.
        log_num = await get_total_logs(str(steam_id))
        if log_num >= 50:
            checks_field += "✅ Logs: " + str(log_num)
        else:
            checks_field += "❌ Logs: " + str(log_num)

        # 2. They have an RGL profile.
        try:
            player_data = await RGL.get_player(steam_id)
        except LookupError:
            checks_field += "\n❌ RGL Profile does not exist"
            registration_embed.add_field(
                name="Checks", value=checks_field, inline=False
            )
            await new_regs_channel.send(embed=registration_embed)
            await registration_channel.send(
                f"""<@{discord_id}> - Your RGL profile does not exist.
                Please create one at https://rgl.gg/?showFront=true and try again."""
            )
            await discord_user.remove_roles(registered_role)
            return

        registration_embed.set_thumbnail(url=player_data["avatar"])
        checks_field += "\n✅ RGL Profile exists"

        # 3. If they have an RGL profile, they have been on a team.
        sixes_top, hl_top = await RGL.get_top_div(steam_id)
        if sixes_top[0] == 0 and hl_top[0] == 0:
            checks_field += "\n❌ No RGL team history"
            await new_regs_channel.send(embed=registration_embed)
            await registration_channel.send(
                f"""<@{discord_id}> - Your registration is being looked
                over manually due to having no RGL history."""
            )
            return

        checks_field += "\n✅ RGL team history exists"

        # 4. If they have an RGL history, they are not banned.
        if await RGL.check_banned(steam_id):
            checks_field += "\n❌ Currently banned from RGL"
            registration_embed.add_field(
                name="Checks", value=checks_field, inline=False
            )
            await new_regs_channel.send(embed=registration_embed)
            await registration_channel.send(
                f"""<@{discord_id}> - You are currently banned from RGL.
                We do not let banned players into pugs.
                Come back after your ban expires."""
            )
            return

        checks_field += "\n✅ Not banned from RGL"

        # 5. If they are ADV/INV, they get the div ban role. Else, give them the right div role.
        await discord_user.remove_roles(nc_am_role, im_ma_role)
        if discord_user.get_role(1060036280970395730) is None:
            if sixes_top[0] >= 5:
                await discord_user.add_roles(six_ban_role)
            if hl_top[0] >= 5:
                await discord_user.add_roles(hl_ban_role)
            if sixes_top[0] >= 5 or hl_top[0] >= 5:
                await div_appeal_channel.send(
                    f"""<@{discord_id}> You have been automatically restricted from normal pugs
                    due to having Advanced/Invite experience in Highlander.\n
                    If you believe that you should be let in (for example, you roster
                    rode on your Advanced seasons), please let us know. Note, this does not mean
                    you are restricted from After Dark pugs."""
                )
        if sixes_top[0] >= 5 or hl_top[0] >= 5:
            await discord_user.add_roles(ad_in_role)
        elif sixes_top[0] >= 3 or hl_top[0] >= 3:
            await discord_user.add_roles(im_ma_role)
        else:
            await discord_user.add_roles(nc_am_role)

        await discord_user.add_roles(sixes_role, hl_role)

        # Send the final registration embed to the new-registrations channel.
        registration_embed.add_field(name="Checks", value=checks_field, inline=False)
        await new_regs_channel.send(embed=registration_embed)

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
            "agg.webserver:app",
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
async def register(registration: agg.NewUser, request: Request):
    """Starts the registration process for a new user.

    Args:
        registration (agg.NewUser): The steam and discord ID of the user
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
            await app.bot.check_new_register_ping(  # pylint: disable=no-member
                int(registration.discord), int(registration.steam)
            )
            return {"message": "Success"}
        return {"message": "Wrong password"}
    print("Incorrect password in headers")
    print(request.headers)


@app.post("/api/send_connect")
async def send_connect(connect: agg.NewConnect, request: Request):
    """Runs the send_connect_dm from the bot using a request with connect info

    Args:
        connect (agg.NewConnect): The connect command
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
