"""Contains the cog to update users roles over time."""

import datetime

import asyncio
import traceback

import nextcord
from nextcord.ext import tasks, commands

import database as db
from test_cog import TestCog
from constants import BOT_COLOR, DEV_UPDATE_LOGS, DEV_CONTRIBUTOR_ROLE
from registration import RegistrationSettings
from rglapi import RglApi, RateLimitException

RGL: RglApi = RglApi()

update_time = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)


class LoadedRegSettings:
    """
    Stores the loaded registration settings for a guild.
    This is different from the normal RegistrationSettings class which just gives the ids for everything.
    Catches a lot of the errors that can happen when trying to load roles/channels.
    """

    def __init__(self, bot: nextcord.Client, settings: RegistrationSettings) -> None:
        guild: nextcord.Guild | None = bot.get_guild(settings.guild_id)
        if guild is None:
            raise AttributeError(
                settings.guild_id, "Guild could not be found. Is the bot in the guild?"
            )
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
                raise AttributeError(
                    settings.roles.registered, "Role could not be found."
                )
            self.registered = guild.get_role(settings.roles.registered)

        # Load channels
        self.registration: nextcord.TextChannel | None
        self.logs: nextcord.TextChannel | None
        if settings.channels.registration is not None:
            reg_channel: nextcord.abc.GuildChannel | None = guild.get_channel(
                settings.channels.registration
            )
            if not isinstance(reg_channel, nextcord.TextChannel):
                raise AttributeError(
                    settings.channels.registration,
                    "Channel could not be found or is not a text channel.",
                )
            self.registration = reg_channel
        else:
            self.registration = None
        if settings.channels.logs is not None:
            log_channel: nextcord.abc.GuildChannel | None = guild.get_channel(
                settings.channels.logs
            )
            if not isinstance(log_channel, nextcord.TextChannel):
                raise AttributeError(
                    settings.channels.logs,
                    "Channel could not be found or is not a text channel.",
                )
            self.logs = log_channel
        else:
            self.logs = None


async def guild_log_failed(settings: LoadedRegSettings, reason: str, data: str) -> None:
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
    embed: nextcord.Embed = nextcord.Embed(
        title=f"Error: {reason}",
        description=data,
        color=BOT_COLOR,
    )
    if settings.logs is not None:
        try:
            await settings.logs.send(embed=embed)
        except nextcord.Forbidden:
            try:
                if settings.registration is not None:
                    await settings.registration.send(embed=embed)
            except nextcord.Forbidden:
                if settings.guild.owner is not None:
                    embed.add_field(
                        name="Why am I being messaged?",
                        value="The bot does not have permission to send messages in the logs channel you set in /registration.\nFix the permissions to avoid these messages.",
                    )
                    await settings.guild.owner.send(embed=embed)


def get_current_roles(
    roles: list[nextcord.Role | None], member: nextcord.Member
) -> set[nextcord.Role]:
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


async def update_player(
    settings: LoadedRegSettings,
    member: nextcord.Member,
    steam_id: int,
    old_roles: list[nextcord.Role],
    new_roles: list[nextcord.Role],
) -> None:
    """Updates the roles of a player to match the new division.

    Parameters
    ----------
    settings : LoadedRegSettings
        The loaded registration settings for the guild.
    member : nextcord.Member
        The member to update.
    steam_id : int
        The steamID64 of the player.
    old_roles : list[nextcord.Role]
        The division roles the player currently has.
    new_roles : list[nextcord.Role]
        The new roles to give the player.
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
                await guild_log_failed(
                    settings,
                    f"Could not remove role {role} from <@{member.id}>.",
                    err.text,
                )
                return

    for role in new_roles:
        if role not in member.roles:
            added_role_string += f"<@&{role.id}> "
            try:
                await member.add_roles(role, reason="Adding new division roles.")
            except nextcord.Forbidden as err:
                await guild_log_failed(
                    settings,
                    f"Could not add role {role} to <@{member.id}>.",
                    err.text,
                )
                return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(
            settings,
            "Could not send message to logs channel.",
            f"<#{settings.logs}>",
        )

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
) -> None:
    """Gives a player the ban role and remove all other division roles.

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
        await member.remove_roles(
            *old_roles, reason="Removing current division roles as part of RGL ban."
        )
        await member.add_roles(ban_role, reason="Adding RGL ban role.")
    except nextcord.Forbidden as err:
        await guild_log_failed(
            settings,
            f"Could not change roles for banned player: <@{member.id}.",
            err.text,
        )
        return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(
            settings,
            "Could not send message to logs channel.",
            f"<#{settings.logs}>",
        )

    ban_embed = nextcord.Embed(
        title="RGL Banned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=0xEB4034,
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
    old_roles: list[nextcord.Role],
    new_roles: list[nextcord.Role],
) -> None:
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
    removed_role_string: str = ""
    # Remove old roles in case the player somehow has division roles
    for role in old_roles:
        if role not in new_roles:
            removed_role_string += f"<@&{role.id}> "
            try:
                await member.remove_roles(role, reason="Removing old division roles.")
            except nextcord.Forbidden as err:
                await guild_log_failed(
                    settings,
                    f"Could not remove role {role} from <@{member.id}>.",
                    err.text,
                )
                return

    try:
        await member.add_roles(
            *new_roles, reason="Adding new division roles as part of unban."
        )
    except nextcord.Forbidden as err:
        await guild_log_failed(
            settings, "Could not change roles for unbanned player.", err.text
        )
        return

    logs_channel: nextcord.TextChannel | None = settings.logs
    if logs_channel is None:
        return
    if not logs_channel.permissions_for(settings.guild.me).send_messages:
        await guild_log_failed(
            settings,
            "Could not send message to logs channel.",
            f"<#{settings.logs}>",
        )

    ban_embed = nextcord.Embed(
        title="RGL Unbanned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=0x26BF36,
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
        value=removed_role_string,
        inline=False,
    )

    await logs_channel.send(embed=ban_embed)


async def update_guild_player(
    settings: LoadedRegSettings,
    player_divs: dict,
    banned: bool,
    steam_id: int,
    discord_id: int,
) -> None:
    """Updates the roles of a player in a guild. Checks whether the player is banned and updates roles accordingly.

    Parameters
    ----------
    settings : LoadedRegSettings
        The loaded registration settings for the guild.
    player_divs : dict
        The player's division data from RGL.
    banned : bool
        Whether the player is banned from RGL.
    steam_id : int
        The steamID64 of the player.
    discord_id : int
        The discord ID of the player.
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
    if settings.gamemode in ("sixes", "both"):
        current_roles.extend(get_current_roles(settings.sixes, member))
        new_roles.append(settings.sixes[player_divs["sixes"][settings.mode]])
    if settings.gamemode in ("highlander", "both"):
        current_roles.extend(get_current_roles(settings.highlander, member))
        new_roles.append(settings.highlander[player_divs["hl"][settings.mode]])
    if settings.gamemode == "combined":
        player_div = max(
            player_divs["sixes"][settings.mode], player_divs["hl"][settings.mode]
        )
        current_roles.extend(
            get_current_roles(settings.sixes, member)
        )  # Both roles are stored in sixes for simplicity
        new_roles.append(settings.sixes[player_div])

    if settings.registered is not None and settings.registered not in member.roles:
        # Player is registered but doesn't have the registered role
        try:
            await member.add_roles(settings.registered)
        except nextcord.Forbidden:
            await guild_log_failed(
                settings, "Could not add registered role.", str(member.id)
            )
            return

    if settings.ban is not None:
        ban_role: nextcord.Role = settings.ban
        old_ban = ban_role in member.roles
        if not old_ban and banned:
            # Player has a new RGL ban
            await ban_player(settings, member, steam_id, current_roles, ban_role)
            return
        if old_ban and banned:
            # Player is still banned, if there are division roles, remove them
            await member.remove_roles(
                *current_roles, reason="Removing division roles as part of RGL ban."
            )
            return
        if old_ban and not banned:
            # Player was recently unbanned from RGL
            current_roles.insert(0, ban_role)
            await unban_player(settings, member, steam_id, current_roles, new_roles)
            return

    if not set(current_roles) == set(new_roles):
        # Player doesn't have the desired role, or has extra roles
        await update_player(settings, member, steam_id, current_roles, new_roles)


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member
        self.admin_log_channel: nextcord.TextChannel | None = None
        log_channel = bot.get_channel(DEV_UPDATE_LOGS)
        if isinstance(log_channel, nextcord.TextChannel):
            self.admin_log_channel = log_channel

    @tasks.loop(time=update_time)
    async def update_rgl(self) -> None:
        """Updates RGL divisions and roles for all registered players in all guilds."""
        # Get all players and servers from DB
        player_cursor = db.get_all_players()
        server_cursor = db.get_all_servers()
        all_players = []
        all_servers = []

        # Gather all information before cursors timeout
        async for server in server_cursor:
            all_servers.append(server)
        async for player in player_cursor:
            all_players.append(player)

        # Go through all servers and add to list if registration is enabled
        guilds: list[LoadedRegSettings] = []
        for server in all_servers:
            settings: RegistrationSettings = RegistrationSettings()
            await settings.load_data(server["guild"])
            if settings.enabled:
                try:
                    guilds.append(LoadedRegSettings(self.bot, settings))
                except AttributeError as err:
                    await self.admin_log_failed(
                        f"Could not load settings for guild {server['guild']}.",
                        str(err),
                    )
                    continue

        # Run the update function for each player
        for player in all_players:
            print(player)
            result: bool = await self.check_player_data(player, guilds)
            if not result:
                await self.admin_log_failed(
                    "Skipping player, update failed.", str(player)
                )
            await asyncio.sleep(3)

    @update_rgl.error
    async def error_handler(self, _exception: BaseException) -> None:
        """Handles errors from the update_rgl loop.

        Parameters
        ----------
        _exception : BaseException
            The exception that was raised
        """
        await self.admin_log_failed(
            "Error in update_rgl loop, updates are stopped.",
            str(traceback.format_exc()),
        )

    async def check_player_data(
        self, player: dict, guilds: list[LoadedRegSettings]
    ) -> bool:
        """Checks the player data and updates their roles in all guilds they are in.

        Parameters
        ----------
        player : dict
            Player data from the database
        guilds : list[LoadedRegSettings]
            List of guild settings to update the player in

        Returns
        -------
        bool
            Whether the player was successfully updated
        """
        attempts: int = 0
        try:
            steam_id = int(player["steam"])
            discord_id = int(player["discord"])
        except KeyError:
            await self.admin_log_failed(
                "Player data missing steam or discord ID.", str(player)
            )
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
                await self.admin_log_failed(
                    "Player not found in RGL database.", str(player)
                )
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
                await self.admin_log_failed(
                    "Player not found in RGL database during ban check.", str(player)
                )
                return False
        if not ban_check:
            await self.admin_log_failed(
                f"Could not check if player {steam_id} is banned.", str(player)
            )
            return False

        # Attempt to update this player in every guild they are in
        for reg_settings in guilds:
            await update_guild_player(
                reg_settings, player_divs, new_ban, steam_id, discord_id
            )

        return True

    async def admin_log_failed(self, reason: str, data: str) -> None:
        """Send a message to the admin log channel about a failed action

        Parameters
        ----------
        reason : str
            The reason the action failed
        data : str
            Any data associated with the error
        """
        embed: nextcord.Embed = nextcord.Embed(
            title=f"Error: {reason}",
            description=data,
            color=BOT_COLOR,
        )
        if self.admin_log_channel is not None:
            await self.admin_log_channel.send(embed=embed)

    @nextcord.slash_command(
        name="update",
        description="Updates RGL divisions and roles for a single member.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def update_guild_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name="discord", description="The user to update.", required=True
        ),
    ) -> None:
        """
        Updates RGL divisions and roles for all registered players in the guild the command was run from
        """
        guild: nextcord.Guild | None = interaction.guild
        if guild is None:
            await interaction.send("This command must be run in a guild.")
            return

        settings: RegistrationSettings = RegistrationSettings()
        await settings.load_data(guild.id)
        if not settings.enabled:
            await interaction.send("Registration is not enabled for this server.")
            return

        loaded: LoadedRegSettings = LoadedRegSettings(self.bot, settings)

        await interaction.response.defer()

        try:
            player: dict = await db.get_player_from_discord(user.id)
        except LookupError:
            await interaction.send("Player not found in database.")
            return

        result: bool = await self.check_player_data(player, [loaded])
        if not result:
            await self.admin_log_failed("Skipping player, update failed.", str(player))
            await interaction.send("Update failed for player.")
        else:
            await interaction.send("Player updated successfully.")

    @nextcord.slash_command(
        name="updateall",
        description="Updates RGL divisions and roles for all registered players in this server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def update_guild_roles(self, interaction: nextcord.Interaction) -> None:
        """
        Updates RGL divisions and roles for all registered players in the guild the command was run from
        """
        guild: nextcord.Guild | None = interaction.guild
        if guild is None:
            await interaction.send("This command must be run in a guild.")
            return

        settings: RegistrationSettings = RegistrationSettings()
        await settings.load_data(guild.id)
        if not settings.enabled:
            await interaction.send("Registration is not enabled for this server.")
            return

        loaded: LoadedRegSettings = LoadedRegSettings(self.bot, settings)

        progress_embed: nextcord.Embed = nextcord.Embed(
            title="Updating Roles",
            description="Updating roles for all registered players...",
            color=BOT_COLOR,
        )
        await interaction.response.send_message(embed=progress_embed)
        # Check each member of the guild
        for member in guild.members:
            if member.bot:
                continue

            try:
                player: dict = await db.get_player_from_discord(member.id)
            except LookupError:
                continue

            progress_embed.clear_fields()
            progress_embed.add_field(
                name="Currently Updating", value=f"<@{member.id}>", inline=True
            )
            await interaction.edit_original_message(embed=progress_embed)

            result: bool = await self.check_player_data(player, [loaded])
            if not result:
                await self.admin_log_failed(
                    "Skipping player, update failed.", str(player)
                )
            await asyncio.sleep(3)  # Avoid rate limiting

        progress_embed.clear_fields()
        progress_embed.title = "Update Complete"
        progress_embed.description = "All registered players have been updated."
        await interaction.edit_original_message(embed=progress_embed)

    @nextcord.slash_command(
        name="clearbypass",
        description="Clears the bypass role from all members in the server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def clear_all_bypasses(self, interaction: nextcord.Interaction):
        """Clears the bypass role from all members in the server.

        Parameters
        ----------
        interaction : nextcord.Interaction
            Interaction object
        """
        guild: nextcord.Guild | None = interaction.guild
        if guild is None:
            await interaction.send("This command must be run in a guild.")
            return

        settings: RegistrationSettings = RegistrationSettings()
        await settings.load_data(guild.id)
        if not settings.enabled:
            await interaction.send("Registration is not enabled for this server.")
            return

        loaded: LoadedRegSettings = LoadedRegSettings(self.bot, settings)

        await interaction.response.defer()
        for member in guild.members:
            if loaded.bypass in member.roles:
                await member.remove_roles(loaded.bypass)
        await interaction.send("Bypass role cleared from all members.")

    @commands.Cog.listener("on_member_join")
    async def new_member(self, member: nextcord.Member) -> None:
        """
        Assigns roles to new members of a server if they are registered.
        """
        settings: RegistrationSettings = RegistrationSettings()
        await settings.load_data(member.guild.id)
        if not settings.enabled:
            return
        loaded: LoadedRegSettings = LoadedRegSettings(self.bot, settings)

        try:
            player: dict = await db.get_player_from_discord(member.id)
        except LookupError:
            return

        await self.check_player_data(player, [loaded])

    @TestCog.test.subcommand(  # pylint: disable=no-member
        name="newjoin",
        description="For testing only. Simulates an existing member as a new guild join",
    )
    async def simulate_new_member(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name="discord", description="The user to simulate.", required=True
        ),
    ):
        """Simulates a new member joining the guild.

        Parameters
        ----------
        interaction : nextcord.Interaction
            The interaction
        user : nextcord.User, optional
            The user to simulate as joining the guild
        """
        if interaction.guild is None:
            await interaction.send("This command must be run in a guild.")
            return

        if (
            not isinstance(interaction.user, nextcord.Member)
            or interaction.user.get_role(DEV_CONTRIBUTOR_ROLE) is None
        ):
            await interaction.send(
                "You do not have the Contributors role and cannot run this command.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(user.id)
        if member is not None:
            await self.new_member(member)
        await interaction.send("Simulated new member join.")

    @TestCog.test.subcommand(  # pylint: disable=no-member
        name="updateall",
        description="For testing only. Runs update loop for all guilds.",
    )
    async def simulate_update_loop(self, interaction: nextcord.Interaction):
        """Simulates the update_rgl loop for all guilds.

        Parameters
        ----------
        interaction : nextcord.Interaction
            The interaction
        """
        if interaction.user is None or isinstance(interaction.user, nextcord.User):
            await interaction.send("This command must be run in a guild.")
            return
        if interaction.guild is None:
            await interaction.send("This command must be run in a guild.")
            return

        if interaction.user.get_role(DEV_CONTRIBUTOR_ROLE) is None:
            await interaction.send(
                "You do not have the Contributors role and cannot run this command.",
                ephemeral=True,
            )
            return
        await interaction.send("Running update loop for all guilds.")
        await self.update_rgl()
        if self.admin_log_channel is not None:
            await self.admin_log_channel.send(
                "Update loop from /test updateall complete."
            )
