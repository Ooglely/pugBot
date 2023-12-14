"""Contains the cog to update users roles over time."""
import datetime

import asyncio
from typing import Optional

import nextcord
from nextcord.ext import tasks, commands

import database as db
from test_cog import TestCog
from constants import BOT_COLOR
from registration import RegistrationSettings
from rglapi import RglApi, RateLimitException

RGL: RglApi = RglApi()

update_time = datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)


def get_guild_old_div(loaded: dict, member: nextcord.Member) -> set[nextcord.Role]:
    """
    Get the guild members current division roles
    :param loaded: Loaded pug registration settings for a guild (see load_guild_settings)
    :param member: Member of the loaded guild
    :return: users current division roles
    """
    # Attempt to get the players current division roles in this guild
    roles = set()
    for role in loaded["roles"]["divisions"]:
        if role in member.roles:
            roles.add(role)

    return roles


async def send_update_embed(loaded, member: nextcord.Member, steam_id, old_roles: set[nextcord.Role],
                            new_role: nextcord.Role):
    """
    Outputs an embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to update
    :param steam_id: Player's steamID64
    :param old_roles: The old roles to remove from the member
    :param new_role: The ban role to add to the member
    :return: None
    """

    logs_channel = loaded["channels"]["log_channel"]
    removed_value = ""

    try:
        for role in old_roles:
            if role == new_role:
                continue
            await member.remove_roles(role)
            removed_value += f"<@&{role.id}> "
        await member.add_roles(new_role)
    except nextcord.DiscordException:
        print("Error adding roles.")
        error_embed = nextcord.Embed(
            title="Error",
            description="There was an error adding roles, please check that the bot has Manage Roles permissions.",
        )
        await logs_channel.send(embed=error_embed)

    log_embed = nextcord.Embed(
        title="Updated Division",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
            + str(steam_id),
        color=BOT_COLOR,
    )
    log_embed.add_field(
        name="Discord", value=f"<@{member.id}>", inline=True
    )
    log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
    log_embed.add_field(
        name="Roles Added",
        value=f"<@&{new_role.id}>",
        inline=False,
    )
    if old_roles:
        log_embed.add_field(
            name="Roles Removed",
            value=removed_value,
            inline=True,
        )
    try:
        await logs_channel.send(embed=log_embed)
    except nextcord.DiscordException:
        print("Error sending embed message.")


async def send_banned_embed(loaded: dict, member: nextcord.Member, steam_id, old_roles: set[nextcord.Role],
                            ban_role: nextcord.Role):
    """
    Outputs a ban embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to ban
    :param steam_id: Player's steamID64
    :param old_roles: The old roles to remove from the member
    :param ban_role: The ban role to add to the member
    :return: None
    """
    logs_channel = loaded["channels"]["log_channel"]
    removed_value = ""

    for role in old_roles:
        if role == ban_role:
            continue
        await member.remove_roles(role)
        removed_value += f"<@&{role.id}> "
    await member.add_roles(ban_role)

    ban_embed = nextcord.Embed(
        title="RGL Banned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
            + str(steam_id),
        color=BOT_COLOR,
    )
    ban_embed.add_field(
        name="Discord", value=f"<@{member.id}>", inline=True
    )
    ban_embed.add_field(
        name="Steam", value=str(steam_id), inline=True
    )
    ban_embed.add_field(
        name="Roles Added",
        value=f"<@&{ban_role.id}>",
        inline=False,
    )
    if old_roles:
        ban_embed.add_field(
            name="Roles Removed",
            value=removed_value,
            inline=True,
        )
    await logs_channel.send(embed=ban_embed)


async def send_unbanned_embed(loaded: dict, member: nextcord.Member, steam_id, ban_role: nextcord.Role,
                              new_role: nextcord.Role):
    """
    Outputs an unban embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to unban
    :param steam_id: Player's steamID64
    :param ban_role: The ban role to remove from the member
    :param new_role: The new division role to give to the member
    :return: None
    """
    logs_channel = loaded["channels"]["log_channel"]

    await member.remove_roles(ban_role)
    await member.add_roles(new_role)

    ban_embed = nextcord.Embed(
        title="RGL Unbanned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
            + str(steam_id),
        color=BOT_COLOR,
    )
    ban_embed.add_field(
        name="Discord", value=f"<@{member.id}>", inline=True
    )
    ban_embed.add_field(
        name="Steam", value=str(steam_id), inline=True
    )
    ban_embed.add_field(
        name="Roles Added",
        value=f"<@&{new_role.id}>",
        inline=False,
    )
    ban_embed.add_field(
        name="Roles Removed",
        value=f"<@&{ban_role.id}>",
        inline=False,
    )
    await logs_channel.send(embed=ban_embed)


async def update_guild_player(loaded: dict, player_divs: dict, banned, steam_id, discord_id):
    """
    Updates a single player and sends messages if the player is updated
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param player_divs: Player division information, see RglApi.get_div_data()
    :param banned: If the player is banned
    :param steam_id: Player's steamID64
    :param discord_id: Player's discord id
    :return: None
    """
    guild = loaded["guild"]
    member: nextcord.Member = guild.get_member(discord_id)
    if member is None:
        # Member is not in this guild
        return

    bypass_role: nextcord.Role | None = loaded["roles"]["bypass"]
    if bypass_role and member.get_role(bypass_role.id):
        # Guild has a valid bypass role and this user has it, skip
        return

    gamemode = loaded["settings"]["gamemode"]
    mode = loaded["settings"]["mode"]

    # Division from RGL
    division = player_divs[gamemode][mode]
    new_role = loaded["roles"]["divisions"][division]

    roles = get_guild_old_div(loaded, member)

    old_ban = loaded["roles"]["rgl_ban"] in member.roles
    if loaded["settings"]["ban"]:
        ban_role = loaded["roles"]["rgl_ban"]
        if not old_ban and banned:
            # Player has a new RGL ban
            await send_banned_embed(loaded, member, steam_id, roles, ban_role)
            return
        elif old_ban and not banned:
            # Player was recently unbanned from RGL
            await send_unbanned_embed(loaded, member, steam_id, ban_role, new_role)
            return

    if new_role not in roles or len(roles) != 1:
        # Player doesn't have the desired role, or has extra roles
        await send_update_embed(loaded, member, steam_id, roles, new_role)


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member

    def load_guild_settings(self, guild_id: int) -> dict | None:
        """
        Loads all guild registration settings, roles, and channels
        :param guild_id: Guild ID to load
        :return: A dictionary containing the information
        """
        guild = self.bot.get_guild(guild_id)

        if guild is None:
            return None

        reg_settings = RegistrationSettings()
        reg_settings.import_from_db(guild_id)

        no_exp_role: nextcord.Role = guild.get_role(reg_settings.roles["noexp"])
        nc_role: nextcord.Role = guild.get_role(reg_settings.roles["newcomer"])
        am_role: nextcord.Role = guild.get_role(reg_settings.roles["amateur"])
        im_role: nextcord.Role = guild.get_role(
            reg_settings.roles["intermediate"]
        )
        main_role: nextcord.Role = guild.get_role(reg_settings.roles["main"])
        adv_role: nextcord.Role = guild.get_role(reg_settings.roles["advanced"])
        inv_role: nextcord.Role = guild.get_role(reg_settings.roles["invite"])
        ban_role: nextcord.Role = guild.get_role(reg_settings.roles["ban"])

        bypass_role = None
        if reg_settings.bypass:
            bypass_role = guild.get_role(reg_settings.roles["bypass"])

        logs_channel: nextcord.TextChannel = guild.get_channel(
            reg_settings.channels["logs"]
        )

        # Yes the double adv_role is intentional...
        # It's to handle people whos top div is Challenger
        divison_roles: list[nextcord.Role] = [
            no_exp_role,
            nc_role,
            am_role,
            im_role,
            main_role,
            adv_role,
            adv_role,
            inv_role,
        ]

        loaded = {
            "guild": guild,
            "roles": {
                "divisions": divison_roles,
                "rgl_ban": ban_role,
                "bypass": bypass_role
            },
            "channels": {
                "log_channel": logs_channel
            },
            "settings": {
                "gamemode": reg_settings.gamemode,
                "mode": reg_settings.mode,
                "ban": reg_settings.ban
            }
        }

        if reg_settings.gamemode == "sixes":
            loaded["settings"]["gamemode"] = "sixes"
        elif reg_settings.gamemode == "highlander":
            loaded["settings"]["gamemode"] = "hl"

        return loaded

    @tasks.loop(time=update_time)  # time=update_time
    async def update_rgl(self):
        """
        Updates RGL divisions and roles for all registered players in all guilds
        """

        # Get all players and servers from DB
        player_cursor = db.get_all_players()
        server_cursor = db.get_all_servers()
        all_players = []
        all_servers = []

        # Gather all information before cursors timeout
        for server in server_cursor:
            all_servers.append(server)
        for player in player_cursor:
            all_players.append(player)

        # Contains tuple pairs of guild objects and their registration settings
        guilds = dict()
        for server in all_servers:
            # If registration settings are not set up, skip
            if "registration" not in server:
                continue
            # If registration is disabled, skip
            if not server["registration"]["enabled"]:
                continue

            guilds[server["guild"]] = self.load_guild_settings(server["guild"])

        for player in all_players:
            print(player)
            steam_id = int(player["steam"])
            discord_id = int(player["discord"])

            # Get updated information from RGL
            player_divs = dict()
            while not player_divs:
                try:
                    player_divs = await RGL.get_div_data(steam_id)
                except RateLimitException as err:
                    print(err, ", waiting and trying again...")
                    await asyncio.sleep(30)
                except LookupError as err:
                    print(err)
                    continue

            try:
                new_ban = await RGL.check_banned(steam_id)
            except LookupError as err:
                print(err, "Somehow this player is registered though??")
                continue

            # Attempt to update this player in every guild they are in
            for loaded in guilds.values():
                await update_guild_player(loaded, player_divs, new_ban, steam_id, discord_id)

    @update_rgl.error
    async def error_handler(self, exception: Exception):
        """Handles printing errors to console for the loop

        Args:
            exception (Exception): The exception that was raised
        """
        print("Error in update_rgl loop:\n")
        print(exception.__class__.__name__)
        print(exception.__cause__)
        print(exception)

    @nextcord.slash_command(
        name="updateall",
        description="Updates RGL divisions and roles for all registered players in this server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def update_guild_roles(self, interaction: nextcord.Interaction):
        """
        Updates RGL divisions and roles for all registered players in the guild the command was run from
        """
        await interaction.send(
            "Updating RGL divisions and roles for all registered players in this server.\nThis will take a while."
        )
        print("Updating players in guild " + str(interaction.guild_id))
        player_cursor = db.get_all_players()

        players = []
        for player in player_cursor:
            players.append(player)
        server = db.get_server(interaction.guild_id)

        # If registration settings are not set up, skip
        if "registration" not in server or not server["registration"]["enabled"]:
            await interaction.send(
                "Can't update, need to enable registration for this server!"
            )
            return

        loaded = self.load_guild_settings(server["guild"])

        for player in players:
            print(player)
            try:
                steam_id = int(player["steam"])
                discord_id = int(player["discord"])
            except KeyError:
                continue
            player_divs = dict()
            try:
                player_divs = await RGL.get_div_data(steam_id)
            except RateLimitException as err:
                print(err, ", waiting and trying again...")
                await asyncio.sleep(30)
            except LookupError as err:
                print(err)
                continue

            try:
                new_ban = await RGL.check_banned(steam_id)
            except LookupError as err:
                print(err, "Somehow this player is registered though??")
                continue

            # Attempt to update this player
            await update_guild_player(loaded, player_divs, new_ban, steam_id, discord_id)

    @commands.Cog.listener("on_member_join")
    async def new_member(self, member: nextcord.Member, banned: Optional[bool] = None):
        """
        Assigns roles to new members of a server if they are registered.
        """
        server = db.get_server(member.guild.id)

        try:
            player = db.get_player_from_discord(member.id)
        except LookupError:
            return

        steam_id = int(player["steam"])

        # If registration settings are not set up, skip
        if "registration" not in server or not server["registration"]["enabled"]:
            return

        loaded = self.load_guild_settings(server["guild"])

        bypass_role: nextcord.Role | None = loaded["roles"]["bypass"]
        if bypass_role and member.get_role(bypass_role.id):
            # Guild has a valid bypass role and this user has it, skip
            return

        # Get updated information from RGL
        player_divs = dict()
        while not player_divs:
            try:
                player_divs = await RGL.get_div_data(steam_id)
            except RateLimitException as err:
                print(err, ", waiting and trying again...")
                await asyncio.sleep(30)
            except LookupError as err:
                print(err)
                continue

        # Normal behavior is to always check RGL API, banned will not be None only in testing
        new_ban = banned
        if banned is None:
            try:
                new_ban = await RGL.check_banned(steam_id)
            except LookupError as err:
                print(err, "Somehow this player is registered though??")
                return

        gamemode = loaded["settings"]["gamemode"]
        mode = loaded["settings"]["mode"]

        # Division from RGL
        division = player_divs[gamemode][mode]
        new_role = loaded["roles"]["divisions"][division]

        roles = get_guild_old_div(loaded, member)
        print(roles)

        removed_value = ""
        ban_role = loaded["roles"]["rgl_ban"]
        if loaded["settings"]["ban"]:
            if new_ban:
                # Player has a new RGL ban
                for role in roles:
                    await member.remove_roles(role)
                    removed_value += f"<@{role.id}> "
                new_role = ban_role
            else:
                await member.remove_roles(ban_role)
                removed_value += f"<@{ban_role.id}> "

        await member.add_roles(new_role)
        log_embed = nextcord.Embed(
            title="New Member",
            url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(player["steam"]),
            color=BOT_COLOR,
        )
        log_embed.add_field(
            name="Discord", value=f"<@{player['discord']}>", inline=True
        )
        log_embed.add_field(name="Steam", value=str(player["steam"]), inline=True)
        log_embed.add_field(
            name="Roles Added",
            value=f"<@&{new_role.id}>",
            inline=False,
        )
        if removed_value:
            log_embed.add_field(
                name="Roles Removed",
                value=removed_value,
                inline=True,
            )

        logs_channel = loaded["channels"]["log_channel"]
        await logs_channel.send(embed=log_embed)
