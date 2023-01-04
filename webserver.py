import json
from discord.ext import commands, tasks
from fastapi import FastAPI, Request
import uvicorn
import asyncio
from pydantic import BaseModel
import os
from rglSearch import rglAPI
from stats import get_total_logs
import discord

API_PASSWORD = os.environ["webapi_password"]

app = FastAPI()


class WebserverCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(start_server())

    @commands.command()
    async def test_registration(self, ctx, discord, steam):
        self.check_new_register_ping(self, discord, steam)

    async def check_new_register_ping(self, discordID: int, steamID: int):
        # Registered Role ID: 1059583976039252108
        user = self.bot.get_guild(952817189893865482).get_member(discordID)
        if user.get_role(1059583976039252108) == None:
            self.register_new_user(self, discordID, steamID)

    async def register_new_user(self, discordID: int, steamID: int):
        agg_server = self.bot.get_guild(952817189893865482)
        discord_user = agg_server.get_member(discordID)
        NCAMrole = agg_server.get_role(992286429881303101)
        IMMArole = agg_server.get_role(992281832437596180)
        ADINrole = agg_server.get_role(1060021145212047391)
        HLBanRole = agg_server.get_role(1060020104462606396)
        SixBanRole = agg_server.get_role(1060020133495578704)
        div_appeal_channel = agg_server.get_channel(1060023899666002001)
        sixes_role = agg_server.get_role(997600373399359608)
        hl_role = agg_server.get_role(997600342306988112)
        new_regs_channel = agg_server.get_channel(1060014665129791528)
        # Setup an embed to send to the new-registrations channel:
        registrationEmbed = discord.Embed(
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

        # We want to check some things to allow a player in automatically:
        # 1. They have at least 50 logs.
        logNum = get_total_logs(steamID)
        if logNum >= 50:
            checks_field += "✅ Logs: " + str(logNum)
        else:
            checks_field += "❌ Logs: " + str(logNum)

        # 2. They have an RGL profile.
        try:
            player_data = rglAPI.get_player(steamID)
        except LookupError:
            checks_field += "\n❌ RGL Profile does not exist"
            print("put error embed here")
            return

        registrationEmbed.set_thumbnail(url=player_data["avatar"])
        checks_field += "\n✅ RGL Profile exists"

        # 3. If they have an RGL profile, they have been on a team.
        sixes_top, hl_top = rglAPI.get_top_div(steamID)
        if sixes_top[0] == 0 and hl_top[0] == 0:
            checks_field += "\n❌ No RGL team history"
            return
        else:
            checks_field += "\n✅ RGL team history exists"

        # 4. If they have an RGL history, they are not banned.
        if rglAPI.check_banned(steamID):
            checks_field += "\n❌ Currently banned from RGL"
            print("put banned embed here")
            return
        else:
            checks_field += "\n✅ Not banned from RGL"

        # 5. If they are ADV/INV, they get the div ban role. Else, give them the right div role.
        if sixes_top >= 5:
            discord_user.add_roles(SixBanRole)
        if hl_top >= 5:
            discord_user.add_roles(HLBanRole)
        if sixes_top >= 5 or hl_top >= 5:
            discord_user.add_roles(ADINrole)
            div_appeal_channel.send(
                f"<@{discordID}> You have been automatically restricted from pugs due to having Advanced/Invite experience in Highlander or 6s.\nIf you believe that you should be let in (with restrictions), please let us know the classes you played in Adv/Inv."
            )
        elif sixes_top >= 3 or hl_top >= 3:
            discord_user.add_roles(IMMArole)
        else:
            discord_user.add_roles(NCAMrole)

        discord_user.add_roles(sixes_role, hl_role)

        # Send the final registration embed to the new-registrations channel.
        registrationEmbed.add_field(name="Checks", value=checks_field, inline=False)
        await new_regs_channel.send(embed=registrationEmbed)


class NewUser(BaseModel):
    steam: str
    discord: str


async def start_server():
    config = uvicorn.Config(
        "webserver:app", host="0.0.0.0", port=1496, log_level="info"
    )
    server = uvicorn.Server(config)
    # server.serve()
    await server.serve()


@app.get("/")
async def hello_world():
    return {"message": "Hello world"}


@app.post("/api/register")
async def register(registration: NewUser, request: Request):
    if "password" in request.headers:
        if request.headers["password"] == API_PASSWORD:
            print(registration.steam)
            print(registration.discord)
            WebserverCog.check_new_register_ping(
                registration.discord, registration.steam
            )
            return {"message": "Hello world"}
        else:
            return {"message": "Wrong password"}
