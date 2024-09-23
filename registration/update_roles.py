"""Contains the cog to update users roles over time."""
import datetime

import asyncio
import logging

import nextcord
from nextcord.ext import tasks, commands
from nextcord.ext.tasks import ET
from nextcord.guild import GuildChannel

import database as db
from test_cog import TestCog
from constants import BOT_COLOR
from registration import RegistrationSettings
from rglapi import RglApi, RateLimitException

RGL: RglApi = RglApi()

update_time = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)


class LoadedRegSettings():
    """
    Stores the loaded registration settings for a guild.
    This is different from the normal RegistrationSettings class which just gives the ids for everything.
    Catches a lot of the errors that can happen when trying to load roles/channels.
    """

    def __init__(self, bot: nextcord.Client, settings: RegistrationSettings) -> None:
        guild: nextcord.Guild | None = bot.get_guild(settings.guild_id)
        if guild is None:
            raise AttributeError(settings.guild_id, "Guild could not be found. Is the bot in the guild?")
        self.guild: nextcord.Guild = guild
        self.gamemode: str = settings.gamemode
        self.mode: str = settings.mode

        # Load sixes roles
        self.sixes: list[nextcord.Role | None] = []
        for role_id in settings.roles.sixes.get_div_list():
            if role_id is None:
                self.sixes.append(None)
            else:
                role = guild.get_role(role_id)
                if role is None:
                    raise AttributeError(role_id, "Role could not be found.")
                self.sixes.append(role)

        # Load highlander roles
        self.highlander: list[nextcord.Role | None] = []
        for role_id in settings.roles.highlander.get_div_list():
            if role_id is None:
                self.highlander.append(None)
            else:
                role = guild.get_role(role_id)
                if role is None:
                    raise AttributeError(role_id, "Role could not be found.")
                self.highlander.append(role)
                
        # Load generic roles
        self.bypass: nextcord.Role | None = None
        self.ban: nextcord.Role | None = None
        self.registered: nextcord.Role | None = None
        if settings.roles.bypass is not None:
            if guild.get_role(settings.roles.bypass) is None:
                raise AttributeError(settings.roles.bypass, "Role could not be found.")
            self.bypass = guild.get_role(settings.roles.bypass)
        if settings.roles.ban is not None:
            if guild.get_role(settings.roles.ban) is None:
                raise AttributeError(settings.roles.ban, "Role could not be found.")
            self.ban = guild.get_role(settings.roles.ban)
        if settings.roles.registered is not None:
            if guild.get_role(settings.roles.registered) is None:
                raise AttributeError(settings.roles.registered, "Role could not be found.")
            self.registered = guild.get_role(settings.roles.registered)

        # Load channels
        self.registration: nextcord.TextChannel | None
        self.logs: nextcord.TextChannel | None
        if settings.channels.registration is not None:
            reg_channel: GuildChannel | None = guild.get_channel(settings.channels.registration)
            if not isinstance(reg_channel, nextcord.TextChannel):
                raise AttributeError(settings.channels.registration, "Channel could not be found or is not a text channel.")
            self.registration = reg_channel
        else:
            self.registration = None
        if settings.channels.logs is not None:
            log_channel: GuildChannel | None = guild.get_channel(settings.channels.logs)
            if not isinstance(log_channel, nextcord.TextChannel):
                raise AttributeError(settings.channels.logs, "Channel could not be found or is not a text channel.")
            self.logs = log_channel
        else:
            self.logs = None


async def guild_log_failed(guild_id: int, reason: str, data: str) -> None:
    """Send a message to the guild or guild owner about a failed action

    Parameters
    ----------
    guild_id : int
        The guild the error happened in
    reason : str
        The reason the action failed
    data : str
        Any data associated with the error
    """
    # TODO: Actually send message to pugbot guild or the guild error happened for (or owner)
    pass

async def admin_log_failed(reason: str, data: str) -> None:
    """Send a message to the admin log channel about a failed action

    Parameters
    ----------
    reason : str
        The reason the action failed
    data : str
        Any data associated with the error
    """
    # TODO: Actually send message to pugbot guild , embed with reason and data
    pass

def get_current_roles(roles: list[nextcord.Role | None], member: nextcord.Member) -> set[nextcord.Role]:
    """Get the current roles of a member

    Parameters
    ----------
    roles : list[nextcord.Role  |  None]
        A role list from the loaded guild settings
    member : nextcord.Member
        The member to get the roles of

    Returns
    -------
    set[nextcord.Role]
        The roles the member has
    """
    current_roles = [role for role in roles if role is not None]
    return set(current_roles) & set(member.roles)
    # TODO: test this lol


async def update_player(
    settings: LoadedRegSettings,
    member: nextcord.Member,
    steam_id: int,
    old_roles: list[nextcord.Role],
    new_roles: list[nextcord.Role],
):
    """
    Outputs an embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to update
    :param steam_id: Player's steamID64
    :param old_roles: The old roles to remove from the member
    :param new_role: The ban role to add to the member
    :return: None
    """
    removed_role_string: str = ""
    added_role_string: str = ""
    # Remove old roles
    for role in old_roles:
        if role not in new_roles:
            removed_role_string += f"<@&{role.id}> "
            try:
                await member.remove_roles(role, reason="Removing old division roles.")
            except nextcord.Forbidden as err:
                await guild_log_failed(settings.guild.id, f"Could not remove role {role} from <@{member.id}>.", err.text)
                return
    
    for role in new_roles:
        if role not in member.roles:
            added_role_string += f"<@&{role.id}> "
            try:
                await member.add_roles(role, reason="Adding new division roles.")
            except nextcord.Forbidden as err:
                await guild_log_failed(settings.guild.id, f"Could not add role {role} to <@{member.id}>.", err.text)
                return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(settings.guild.id, "Could not send message to logs channel.", f"<#{settings.logs}>")

    log_embed = nextcord.Embed(
        title="Updated Division",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=BOT_COLOR,
    )
    log_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
    log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
    if removed_role_string:
        log_embed.add_field(
            name="Roles Removed",
            value=removed_role_string,
            inline=False,
        )
    if added_role_string:
        log_embed.add_field(
            name="Roles Added",
            value=added_role_string,
            inline=False,
        )
        
    await logs_channel.send(embed=log_embed)


async def ban_player(
    settings: LoadedRegSettings,
    member: nextcord.Member,
    steam_id: int,
    old_roles: list[nextcord.Role],
    ban_role: nextcord.Role,
):
    """Gives a player the ban role and removed all other division roles.

    Parameters
    ----------
    settings : LoadedRegSettings
        Loaded registration settings for the guild.
    member : nextcord.Member
        The member to ban.
    steam_id : int
        The steamID64 of the player.
    old_roles : list[nextcord.Role]
        The roles the player currently has.
    ban_role : nextcord.Role
        The ban role to give the player
    """
    try:
        await member.remove_roles(*old_roles, reason="Removing current division roles as part of RGL ban.")
        await member.add_roles(ban_role, reason="Adding RGL ban role.")
    except nextcord.Forbidden as err:
        await guild_log_failed(settings.guild.id, f"Could not change roles for banned player: <@{member.id}.", err.text)
        return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(settings.guild.id, "Could not send message to logs channel.", f"<#{settings.logs}>")

    ban_embed = nextcord.Embed(
        title="RGL Banned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=0xeb4034,
    )
    ban_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)
    ban_embed.add_field(
        name="Roles Added",
        value=f"<@&{ban_role.id}>",
        inline=False,
    )
    if old_roles:
        removed_value = ""
        for role in old_roles:
            removed_value += f"<@&{role.id}> "
        ban_embed.add_field(
            name="Roles Removed",
            value=removed_value,
            inline=True,
        )

    await logs_channel.send(embed=ban_embed)


async def unban_player(
    settings: LoadedRegSettings,
    member: nextcord.Member,
    steam_id: int,
    ban_role: nextcord.Role,
    new_roles: list[nextcord.Role],
):
    """Removes the ban role from a player and adds the new division roles.

    Parameters
    ----------
    settings : LoadedRegSettings
        The loaded registration settings for the guild.
    member : nextcord.Member
        The member to unban.
    steam_id : int
        The steamID64 of the player.
    ban_role : nextcord.Role
        The ban role to remove.
    new_roles : list[nextcord.Role]
        The new roles to add.
    """
    try:
        await member.remove_roles(ban_role, reason="Removing RGL ban role.")
        await member.add_roles(*new_roles, reason="Adding new division roles as part of unban.")
    except nextcord.Forbidden as err:
        await guild_log_failed(settings.guild.id, "Could not change roles for unbanned player.", err.text)
        return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(settings.guild.id, "Could not send message to logs channel.", f"<#{settings.logs}>")

    ban_embed = nextcord.Embed(
        title="RGL Unbanned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=0x26bf36,
    )
    ban_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)

    add_field = ""
    if new_roles:
        for role in new_roles:
            add_field += f"<@&{role.id}> "
        ban_embed.add_field(
            name="Roles Added",
            value=add_field,
            inline=False,
        )
    ban_embed.add_field(
        name="Roles Removed",
        value=f"<@&{ban_role.id}>",
        inline=False,
    )

    await logs_channel.send(embed=ban_embed)


async def update_guild_player(
    settings: LoadedRegSettings, player_divs: dict, banned: bool, steam_id: int, discord_id: int
):
    """
    Updates a single player and sends messages if the player is updated
    """
    member: nextcord.Member | None = settings.guild.get_member(discord_id)
    if member is None:
        # Member is not in this guild
        return

    if settings.bypass and member.get_role(settings.bypass.id):
        # Guild has a valid bypass role and this user has it, skip
        return

    # Division from RGL
    current_roles: list[nextcord.Role] = []
    new_roles: list[nextcord.Role] = []
    if settings.gamemode in ("sixes", "combined", "both"):
        current_roles.extend(get_current_roles(settings.sixes, member))
        new_roles += settings.sixes[player_divs["sixes"][settings.mode]]
    if settings.gamemode in ("highlander", "both"):
        current_roles.extend(get_current_roles(settings.highlander, member))
        new_roles += settings.highlander[player_divs["hl"][settings.mode]]

    if settings.ban is not None:
        ban_role: nextcord.Role = settings.ban
        old_ban = ban_role in member.roles
        if not old_ban and banned:
            # Player has a new RGL ban
            await ban_player(settings, member, steam_id, current_roles, ban_role)
            return
        if old_ban and not banned:
            # Player was recently unbanned from RGL
            await unban_player(settings, member, steam_id, ban_role, new_roles)
            return

    if not all(role in current_roles for role in new_roles):
        # Player doesn't have the desired role, or has extra roles
        await update_player(settings, member, steam_id, current_roles, new_roles)

    if (
        settings.registered is not None
        and settings.registered not in member.roles
    ):
        # Player is registered but doesn't have the registered role
        try:
            await member.add_roles(settings.registered)
        except nextcord.Forbidden:
            await guild_log_failed(settings.guild.id, "Could not add registered role.", str(member.id))


async def check_player_data(player: dict, guilds: list[LoadedRegSettings]) -> bool:
    """
    Retrieves updated player data from RGL and updates the database
    :param player: The player to check
    :return: True if the player has the required data
    """
    attempts: int = 0
    try:
        steam_id = int(player["steam"])
        discord_id = int(player["discord"])
    except KeyError:
        await admin_log_failed("Player data missing steam or discord ID.", str(player))
        return False

    # Get updated information from RGL
    player_divs: dict[str, dict[str, int]] = {}
    while not player_divs and attempts < 3:
        try:
            player_divs = await RGL.get_div_data(steam_id)
        except RateLimitException as err:
            print(err, ", waiting and trying again...")
            await asyncio.sleep(60)
            attempts += 1
        except LookupError:
            await admin_log_failed("Player not found in RGL database.", str(player))
            return False
    if player_divs == {}:
        return False
    await db.update_divisons(steam_id, player_divs)
    ban_check: bool = False
    new_ban: bool
    while not ban_check and attempts < 3:
        try:
            new_ban = await RGL.check_banned(steam_id)
            ban_check = True
        except RateLimitException as err:
            print(err, ", waiting and trying again...")
            await asyncio.sleep(60)
            attempts += 1
        except LookupError as err:
            await admin_log_failed("Player not found in RGL database during ban check.", str(player))
            return False
    if not ban_check:
        await admin_log_failed(f"Could not check if player {steam_id} is banned.", str(player))
        return False

    # Attempt to update this player in every guild they are in
    for reg_settings in guilds:
        await update_guild_player(reg_settings, player_divs, new_ban, steam_id, discord_id)

    return True


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member

    @tasks.loop(time=update_time)
    async def update_rgl(self) -> None:
        """Updates RGL divisions and roles for all registered players in all guilds."""
        pass

    @update_rgl.error
    async def error_handler(self, _exception: BaseException) -> None:
        """Handles errors from the update_rgl loop.

        Parameters
        ----------
        _exception : BaseException
            The exception that was raised
        """

    @nextcord.slash_command(
        name="updateall",
        description="Updates RGL divisions and roles for all registered players in this server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def update_guild_roles(self, interaction: nextcord.Interaction):
        """
        Updates RGL divisions and roles for all registered players in the guild the command was run from
        """

    @commands.Cog.listener("on_member_join")
    async def new_member(self, member: nextcord.Member):
        """
        Assigns roles to new members of a server if they are registered.
        """

    @TestCog.test.subcommand(  # pylint: disable=no-member
        name="newjoin",
        description="For testing only. Simulates an existing member as a new guild join",
    )
    async def simulate_new_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name="discord", description="The user to look up.", required=True
        ),
    ):
        """
        Command to simulate a member joining the guild, can pretend that a user is RGL banned
        :param interaction: The interaction
        :param user: User to simulate
        :param banned: Optional fake RGL ban or not
        :return: None
        """

    @TestCog.test.subcommand(  # pylint: disable=no-member
        name="updateall",
        description="For testing only. Runs update loop for all guilds.",
    )
    async def simulate_update_loop(self, interaction: nextcord.Interaction):
        """
        Command to simulate the update loop for all guilds
        :param interaction: The interaction
        :return: None
        """
        # TODO: Make this an owner only command
