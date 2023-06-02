import nextcord
import util
from fastapi import FastAPI, Request
import uvicorn
import asyncio
from rglAPI import rglAPI
from agg.stats import get_total_logs
import agg
from constants import API_PASSWORD, PORT

app = FastAPI()
rglAPI = rglAPI()


class WebserverCog(nextcord.ext.commands.Cog):
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
        await interaction.response.defer()
        await self.check_new_register_ping(
            int(discord_user.id), int(util.get_steam64(steam_id))
        )
        await interaction.send(
            f"User registered.\nSteam: `{util.get_steam64(steam_id)}`\nDiscord: `{discord_user.id}`",
            ephemeral=True,
        )

    # @commands.command(pass_context=False)
    async def check_new_register_ping(self, discordID: int, steamID: int):
        # Registered Role ID: 1059583976039252108
        new_regs_channel = self.bot.get_guild(952817189893865482).get_channel(
            1060014665129791528
        )
        user = self.bot.get_guild(952817189893865482).get_member(discordID)
        if user == None:
            await new_regs_channel.send(
                f"New registration not found in server: {discordID}"
            )
            print("User not found in server")
            return "User not found in server"
        if user.get_role(1059583976039252108) == None:
            await self.register_new_user(discordID, steamID)

    async def register_new_user(self, discordID: int, steamID: int):
        agg_server: nextcord.Guild = self.bot.get_guild(952817189893865482)

        discord_user: nextcord.Member = agg_server.get_member(discordID)

        div_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
            1060023899666002001
        )
        new_regs_channel: nextcord.TextChannel = agg_server.get_channel(
            1060014665129791528
        )
        registration_channel: nextcord.TextChannel = agg_server.get_channel(
            996607763159457812
        )

        NCAMrole: nextcord.Role = agg_server.get_role(992286429881303101)
        IMMArole: nextcord.Role = agg_server.get_role(992281832437596180)
        ADINrole: nextcord.Role = agg_server.get_role(1060021145212047391)
        HLBanRole: nextcord.Role = agg_server.get_role(1060020104462606396)
        SixBanRole: nextcord.Role = agg_server.get_role(1060020133495578704)

        sixes_role: nextcord.Role = agg_server.get_role(997600373399359608)
        hl_role: nextcord.Role = agg_server.get_role(997600342306988112)

        registered_role: nextcord.Role = agg_server.get_role(1059583976039252108)

        # Give registered role
        await discord_user.add_roles(registered_role)

        # Setup an embed to send to the new-registrations channel:
        registrationEmbed = nextcord.Embed(
            title="New Registration",
            url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steamID),
            color=0xFFFFFF,
        )
        registrationEmbed.add_field(
            name="Discord", value=f"<@{discordID}>", inline=True
        )
        registrationEmbed.add_field(name="Steam", value=str(steamID), inline=True)

        # We will add a checks field later, but want to add data to it as we go along the process.
        checks_field = ""

        # Since we have started the registration process we can delete the messages the user has sent in #pug-registration
        # (if they have anyways)
        async for message in registration_channel.history(limit=100):
            if message.author.id == discordID:
                await message.delete()

        # We want to check some things to allow a player in automatically:
        # 1. They have at least 50 logs.
        logNum = await get_total_logs(steamID)
        if logNum >= 50:
            checks_field += "✅ Logs: " + str(logNum)
        else:
            checks_field += "❌ Logs: " + str(logNum)

        # 2. They have an RGL profile.
        try:
            player_data = await rglAPI.get_player(steamID)
        except LookupError:
            checks_field += "\n❌ RGL Profile does not exist"
            registrationEmbed.add_field(name="Checks", value=checks_field, inline=False)
            await new_regs_channel.send(embed=registrationEmbed)
            await registration_channel.send(
                f"<@{discordID}> - Your RGL profile does not exist. Please create one at https://rgl.gg/?showFront=true and try again."
            )
            await discord_user.remove_roles(registered_role)
            return

        registrationEmbed.set_thumbnail(url=player_data["avatar"])
        checks_field += "\n✅ RGL Profile exists"

        # 3. If they have an RGL profile, they have been on a team.
        sixes_top, hl_top = await rglAPI.get_top_div(steamID)
        if sixes_top[0] == 0 and hl_top[0] == 0:
            checks_field += "\n❌ No RGL team history"
            await new_regs_channel.send(embed=registrationEmbed)
            await registration_channel.send(
                f"<@{discordID}> - Your registration is being looked over manually due to having no RGL history."
            )
            return
        else:
            checks_field += "\n✅ RGL team history exists"

        # 4. If they have an RGL history, they are not banned.
        if await rglAPI.check_banned(steamID):
            checks_field += "\n❌ Currently banned from RGL"
            registrationEmbed.add_field(name="Checks", value=checks_field, inline=False)
            await new_regs_channel.send(embed=registrationEmbed)
            await registration_channel.send(
                f"<@{discordID}> - You are currently banned from RGL. We do not let banned players into pugs. Come back after your ban expires."
            )
            return
        else:
            checks_field += "\n✅ Not banned from RGL"

        # 5. If they are ADV/INV, they get the div ban role. Else, give them the right div role.
        await discord_user.remove_roles(NCAMrole, IMMArole)
        if discord_user.get_role(1060036280970395730) == None:
            if sixes_top[0] >= 5:
                await discord_user.add_roles(SixBanRole)
            if hl_top[0] >= 5:
                await discord_user.add_roles(HLBanRole)
            if sixes_top[0] >= 5 or hl_top[0] >= 5:
                await div_appeal_channel.send(
                    f"<@{discordID}> You have been automatically restricted from pugs due to having Advanced/Invite experience in Highlander or 6s.\nIf you believe that you should be let in (for example, you roster rode on your Advanced seasons), please let us know."
                )
        if sixes_top[0] >= 5 or hl_top[0] >= 5:
            await discord_user.add_roles(ADINrole)
        elif sixes_top[0] >= 3 or hl_top[0] >= 3:
            await discord_user.add_roles(IMMArole)
        else:
            await discord_user.add_roles(NCAMrole)

        await discord_user.add_roles(sixes_role, hl_role)

        # Send the final registration embed to the new-registrations channel.
        registrationEmbed.add_field(name="Checks", value=checks_field, inline=False)
        await new_regs_channel.send(embed=registrationEmbed)

    async def send_connect_dm(self, discordID: int, connectCommand: str):
        connectEmbed = nextcord.Embed(
            title="New Connect",
            color=0xF0984D,
        )
        connectEmbed.add_field(name="Connect Command", value=connectCommand)
        await self.bot.get_user(int(discordID)).send(embed=connectEmbed)

    async def start_server(self):
        config = uvicorn.Config(
            "agg.webserver:app",
            host="0.0.0.0",
            port=PORT,
            log_level="info",
        )
        server = uvicorn.Server(config)
        app.bot: WebserverCog = self
        await server.serve()

    @app.get("/")
    async def hello_world():
        return {"message": "Hello world"}

    @app.post("/api/register")
    async def register(registration: agg.NewUser, request: Request):
        print(registration)
        if "password" in request.headers:
            if request.headers["password"] == API_PASSWORD:
                print(registration.steam)
                print(registration.discord)
                await asyncio.sleep(3)
                await app.bot.check_new_register_ping(
                    int(registration.discord), int(registration.steam)
                )
                return {"message": "Success"}
            else:
                return {"message": "Wrong password"}
        else:
            print("Incorrect password in headers")
            print(request.headers)

    @app.post("/api/send_connect")
    async def send_connect(connect: agg.NewConnect, request: Request):
        print(connect)
        if request.headers["user-agent"].startswith("sm-ripext"):
            print(connect.discordID)
            print(connect.connectCommand)
            await app.bot.send_connect_dm(
                int(connect.discordID), str(connect.connectCommand)
            )
            return {"message": "Success"}
        else:
            print("Request not from TF2 plugin")
            print(request.headers)
            return {"message": "Wrong password"}
