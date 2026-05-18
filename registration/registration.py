"""Contains the webserver cog, which is responsible for the webserver and registering users."""

import aiohttp
import nextcord
from nextcord.ext.commands import Cog, Bot
from nextcord.ext.application_checks import is_owner
import uvicorn
from fastapi import FastAPI

import util
from constants import (
    PRIVILEGED_GUILDS,
    BOT_COLOR,
    PORT,
    DEV_REGISTRATIONS,
    DEV_DISCORD_LINK,
)
from database import (
    add_player,
    get_all_servers,
    update_divisons,
    get_player_from_steam,
    get_player_from_discord,
    BotCollection,
)
from registration import RegistrationSettings
from registration.update_roles import LoadedRegSettings, update_guild_player
from rglapi import RglApi

RGL: RglApi = RglApi()
player_db: BotCollection = BotCollection("players", "data")


class RegistrationCog(Cog):
    """Cog that stores all the functions to register users."""

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.admin_log_channel: nextcord.TextChannel | None = None
        channel = bot.get_channel(DEV_REGISTRATIONS)
        if isinstance(channel, nextcord.TextChannel):
            self.admin_log_channel = channel

    @nextcord.slash_command(
        name="register",
        description="Manually register a user in the database.",
        guild_ids=PRIVILEGED_GUILDS,
    )
    @util.is_runner()
    async def manual_registration(
        self,
        interaction: nextcord.Interaction,
        discord_user: nextcord.User,
        steam_id: str,
    ) -> None:
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
            await interaction.send(
                f"User registered.\nSteam: `{util.get_steam64(steam_id)}`\nDiscord: `{discord_user.id}`",
                ephemeral=True,
            )
        else:
            # Registration failed
            await interaction.send(
                f"Error occurred while manually registering user: `{result}`",
                ephemeral=True,
            )

    @nextcord.slash_command(
        name="unregister",
        description="Manually delete a user in the database.",
        guild_ids=PRIVILEGED_GUILDS,
    )
    @is_owner()
    async def delete_user(
        self,
        interaction: nextcord.Interaction,
        steam: str | None = nextcord.SlashOption(name="steam", required=None),
        discord: nextcord.User | None = nextcord.SlashOption(
            name="discord", required=False
        ),
    ):
        """Deletes a user from the database.

        Args:
            steam (int | None): The steam id of the user to delete if provided
            discord (nextcord.User | None): The discord user to delete if provided
        """
        if not steam and not discord:
            await interaction.send("You must provide either a steam or discord id.")
            return
        if steam:
            await player_db.delete_item({"steam": str(steam)})
        elif discord:
            await player_db.delete_item({"discord": str(discord.id)})
        await interaction.send("User deleted.")

    async def register_new_user(self, discord_id: int, steam_id: int) -> str | None:
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

        Returns a string describing an error if the registration was not successful, else None
        """
        user = self.bot.get_user(discord_id)
        if user is None:
            return "Bot was unable to find discord user."

        try:
            player = await get_player_from_steam(steam_id)
            if player is not None and player["discord"] == str(discord_id):
                return (
                    f"Your Steam and Discord accounts are already linked to each other. If this is an error, "
                    f"please contact PugBot devs @ {DEV_DISCORD_LINK}"
                )
            return f"Steam profile is already linked. Please contact PugBot devs {DEV_DISCORD_LINK}"
        except LookupError:
            # pass is not a mistake or incomplete implementation, this means the steam is unique and we can proceed
            pass

        try:
            await get_player_from_discord(discord_id)
            return f"Discord is already linked. Please contact PugBot devs {DEV_DISCORD_LINK}"
        except LookupError:
            # pass is not a mistake or incomplete implementation, this means the steam is unique and we can proceed
            pass

        # If the user doesn't have an RGL profile, don't bother registering
        try:
            player_data = await RGL.get_player(steam_id)
        except LookupError:
            return "RGL profile does not exist. Please create one at https://rgl.gg/ and try again."

        # Gather player data and
        player_divs = await RGL.get_div_data(steam_id)
        current_ban = await RGL.check_banned(steam_id)
        try:
            log_num = await util.get_total_logs(str(steam_id))
        except aiohttp.ClientResponseError:
            return "Unable to get logs from logs.tf. Please try again."

        # Add the player to the database
        await add_player(str(steam_id), str(user.id))
        await update_divisons(steam_id, player_divs)

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
        if self.admin_log_channel is not None:
            await self.admin_log_channel.send(embed=registration_embed)

        # Avoid cursor timeout
        all_servers = []
        async for server in get_all_servers():
            all_servers.append(server)

        for server in all_servers:
            # Load this guild's settings, roles, and channels from the DB
            settings: RegistrationSettings = RegistrationSettings()
            await settings.load_data(server["guild"])
            if not settings.enabled:
                continue
            try:
                loaded: LoadedRegSettings = LoadedRegSettings(self.bot, settings)
            except AttributeError:
                continue
            except ValueError:
                continue

            # If member is not in server, skip
            member: nextcord.Member | None = loaded.guild.get_member(discord_id)
            if member is None:
                continue

            # guh I hate this but I don't want to pass the other cog to this cog
            # and I still want to show the new roles in the reg message
            current_roles: set[nextcord.Role] = set(member.roles)
            await update_guild_player(
                loaded, player_divs, current_ban, steam_id, discord_id
            )
            new_roles: set[nextcord.Role] = set(member.roles)

            new_roles_str = ""
            for role in new_roles - current_roles:
                new_roles_str += f"<@&{role.id}> "

            if new_roles_str == "":
                new_roles_str = "None"

            registration_embed.add_field(
                name="Roles Added",
                value=new_roles_str,
                inline=False,
            )
            if loaded.registration is not None:
                await loaded.registration.send(embed=registration_embed)

            # Remove the last 2 fields in preparation for the next guild
            registration_embed.remove_field(-1)
        return None

    async def start_server(self: Cog, asgi: FastAPI):
        """Starts the uvicorn webserver with the correct config."""
        config = uvicorn.Config(
            asgi,
            host="",
            port=PORT,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
