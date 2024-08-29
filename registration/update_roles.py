"""Contains the cog to update users roles over time."""
import datetime
import traceback

import asyncio
import logging

import nextcord
from nextcord.ext import tasks, commands

import database as db
from test_cog import TestCog
from constants import BOT_COLOR
from registration import RegistrationSettings
from rglapi import RglApi, RateLimitException

RGL: RglApi = RglApi()

update_time = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)


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


async def send_update_embed(
    loaded,
    member: nextcord.Member,
    steam_id,
    old_roles: set[nextcord.Role],
    new_role: nextcord.Role,
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

    # If the role it is trying to add doesn't exist it's going to cause issues
    if new_role is None:
        return

    logs_channel = loaded["channels"]["logs"]
    if logs_channel is None:
        print("Error, logs channel not set up.")
        print(loaded)
        return
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
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=BOT_COLOR,
    )
    log_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
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


async def send_banned_embed(
    loaded: dict,
    member: nextcord.Member,
    steam_id,
    old_roles: set[nextcord.Role],
    ban_role: nextcord.Role,
):
    """
    Outputs a ban embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to ban
    :param steam_id: Player's steamID64
    :param old_roles: The old roles to remove from the member
    :param ban_role: The ban role to add to the member
    :return: None
    """
    logs_channel = loaded["channels"]["logs"]
    if logs_channel is None:
        print("Error, logs channel not set up.")
        return
    removed_value = ""

    ban_embed = nextcord.Embed(
        title="RGL Banned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=BOT_COLOR,
    )
    ban_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)
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

    try:
        for role in old_roles:
            if role == ban_role:
                continue
            await member.remove_roles(role)
            removed_value += f"<@&{role.id}> "
        await member.add_roles(ban_role)
    except nextcord.DiscordException:
        ban_embed.add_field(
            name="Error",
            value="There was an error changing roles, please check that the bot has Manage Roles permissions, and change this users roles manually.",
        )

    await logs_channel.send(embed=ban_embed)


async def send_unbanned_embed(
    loaded: dict,
    member: nextcord.Member,
    steam_id,
    ban_role: nextcord.Role,
    new_role: nextcord.Role,
):
    """
    Outputs an unban embed to the member's discord and updates the members roles
    :param loaded: The loaded settings, see Update_Roles_Cog.load_guild_settings()
    :param member: Discord member to unban
    :param steam_id: Player's steamID64
    :param ban_role: The ban role to remove from the member
    :param new_role: The new division role to give to the member
    :return: None
    """
    logs_channel = loaded["channels"]["logs"]
    if logs_channel is None:
        print("Error, logs channel not set up.")
        return

    ban_embed = nextcord.Embed(
        title="RGL Unbanned Player",
        url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
        color=BOT_COLOR,
    )
    ban_embed.add_field(name="Discord", value=f"<@{member.id}>", inline=True)
    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)
    try:
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
    except AttributeError:
        ban_embed.add_field(
            name="Error",
            value="There was an error getting one of the roles for this server. Please check that the roles in /registration still exist.",
            inline=False,
        )

    try:
        await member.remove_roles(ban_role)
        await member.add_roles(new_role)
    except nextcord.DiscordException:
        ban_embed.add_field(
            name="Error",
            value="There was an error changing roles, please check that the bot has Manage Roles permissions, and change this users roles manually.",
        )

    try:
        await logs_channel.send(embed=ban_embed)
    except nextcord.DiscordException:
        print(f"Error sending embed message in guild {str(member.guild.id)}")


async def update_guild_player(
    loaded: dict, player_divs: dict, banned, steam_id, discord_id
):
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

    game_mode = loaded["settings"]["game_mode"]
    mode = loaded["settings"]["mode"]

    # Division from RGL
    division = player_divs[game_mode][mode]
    new_role = loaded["roles"]["divisions"][division]

    roles = get_guild_old_div(loaded, member)

    old_ban = loaded["roles"]["rgl_ban"] in member.roles
    if loaded["settings"]["ban"]:
        ban_role = loaded["roles"]["rgl_ban"]
        if not old_ban and banned:
            # Player has a new RGL ban
            await send_banned_embed(loaded, member, steam_id, roles, ban_role)
            return
        if old_ban and not banned:
            # Player was recently unbanned from RGL
            await send_unbanned_embed(loaded, member, steam_id, ban_role, new_role)
            return

    if new_role not in roles or len(roles) != 1:
        # Player doesn't have the desired role, or has extra roles
        await send_update_embed(loaded, member, steam_id, roles, new_role)

    if (
        loaded["roles"]["registered"] is not None
        and loaded["roles"]["registered"] not in member.roles
    ):
        # Player is registered but doesn't have the registered role
        await member.add_roles(loaded["roles"]["registered"])


async def check_player_data(player: dict, guilds: dict[str, dict | None]) -> bool:
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
        except LookupError as err:
            print(err)
            await asyncio.sleep(15)
            attempts += 1
    if player_divs == {}:
        return False
    await db.update_divisons(steam_id, player_divs)
    ban_check: bool = False
    while not ban_check and attempts < 3:
        try:
            new_ban = await RGL.check_banned(steam_id)
            ban_check = True
        except RateLimitException as err:
            print(err, ", waiting and trying again...")
            await asyncio.sleep(60)
            attempts += 1
        except LookupError as err:
            print(err, "Somehow this player is registered though??")
            await asyncio.sleep(15)
            attempts += 1
    if not ban_check:
        return False

    # Attempt to update this player in every guild they are in
    for loaded in guilds.values():
        if loaded is not None:
            await update_guild_player(
                loaded, player_divs, new_ban, steam_id, discord_id
            )

    return True


def load_guild_settings(bot: nextcord.Client, guild_id: int) -> dict | None:
    """
    Loads all guild registration settings, roles, and channels
    :param bot: The nextcord bot client
    :param guild_id: Guild ID to load
    :return: A dictionary containing the information
    """
    guild = bot.get_guild(guild_id)

    if guild is None:
        return None

    reg_settings = RegistrationSettings()
    reg_settings.import_from_db(guild_id)

    no_exp_role: nextcord.Role = guild.get_role(reg_settings.roles["noexp"])
    nc_role: nextcord.Role = guild.get_role(reg_settings.roles["newcomer"])
    am_role: nextcord.Role = guild.get_role(reg_settings.roles["amateur"])
    im_role: nextcord.Role = guild.get_role(reg_settings.roles["intermediate"])
    main_role: nextcord.Role = guild.get_role(reg_settings.roles["main"])
    adv_role: nextcord.Role = guild.get_role(reg_settings.roles["advanced"])
    inv_role: nextcord.Role = guild.get_role(reg_settings.roles["invite"])
    ban_role: nextcord.Role = guild.get_role(reg_settings.roles["ban"])
    try:
        registered_role: nextcord.Role | None = guild.get_role(
            reg_settings.roles["registered"]
        )
    except KeyError:
        registered_role = None

    bypass_role = None
    if reg_settings.bypass:
        bypass_role = guild.get_role(reg_settings.roles["bypass"])

    logs_channel: nextcord.TextChannel = guild.get_channel(
        reg_settings.channels["logs"]
    )
    registration_channel: nextcord.TextChannel = guild.get_channel(
        reg_settings.channels["registration"]
    )

    # Yes the double adv_role is intentional...
    # It's to handle people whos top div is Challenger
    division_roles: list[nextcord.Role] = [
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
            "divisions": division_roles,
            "rgl_ban": ban_role,
            "bypass": bypass_role,
            "registered": registered_role,
        },
        "channels": {"logs": logs_channel, "registration": registration_channel},
        "settings": {
            "game_mode": reg_settings.gamemode,
            "mode": reg_settings.mode,
            "ban": reg_settings.ban,
        },
    }

    if reg_settings.gamemode == "sixes":
        loaded["settings"]["game_mode"] = "sixes"
    elif reg_settings.gamemode == "highlander":
        loaded["settings"]["game_mode"] = "hl"

    return loaded


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member

    @tasks.loop(time=update_time)
    async def update_rgl(self) -> None:
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
        guilds: dict[str, dict | None] = {}
        for server in all_servers:
            # If registration settings are not set up, skip
            if "registration" not in server:
                continue
            # If registration is disabled, skip
            if not server["registration"]["enabled"]:
                continue

            guilds[server["guild"]] = load_guild_settings(self.bot, server["guild"])

        for player in all_players:
            result: bool = await check_player_data(player, guilds)
            if result is False:
                print(f"Error updating player {player}, skipping...")
                await self.bot.get_channel(1259641880015147028).send(
                    f"Error updating player {player}, skipping..."
                )
            await asyncio.sleep(15)  # No spamming!

        await self.bot.get_channel(1259641880015147028).send(
            "Finished updating RGL divisions and roles for all registered players in all servers."
        )

    @update_rgl.error
    async def error_handler(self, _exception: Exception):
        """Handles printing errors to console for the loop

        Args:
            exception (Exception): The exception that was raised
        """
        print("Error in update_rgl loop:\n")
        print(traceback.format_exc())
        await self.bot.get_channel(1259641880015147028).send(traceback.format_exc())

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

        loaded = load_guild_settings(self.bot, server["guild"])

        for player in players:
            try:
                member: nextcord.Member | None = interaction.guild.get_member(
                    int(player["discord"])
                )
                if member is None:
                    # Member is not in this guild
                    continue
            except KeyError:
                continue
            try:
                await interaction.edit_original_message(
                    content=f"Updating RGL divisions and roles for all registered players in this server.\nThis will take a while.\nUpdating player <@{player['discord']}>..."
                )
            except nextcord.HTTPException:
                pass

            result: bool = await check_player_data(
                player, {str(interaction.guild_id): loaded}
            )
            if result is False:
                print(f"Error updating player {player}, skipping...")
                continue
            await asyncio.sleep(15)  # No spamming!
        try:
            await interaction.send(
                content="Finished updating RGL divisions and roles for all registered players in this server."
            )
        except nextcord.HTTPException:
            pass

    @commands.Cog.listener("on_member_join")
    async def new_member(self, member: nextcord.Member):
        """
        Assigns roles to new members of a server if they are registered.
        """
        server = db.get_server(member.guild.id)

        try:
            player = db.get_player_from_discord(member.id)
        except LookupError:
            return

        # If registration settings are not set up, skip
        if "registration" not in server or not server["registration"]["enabled"]:
            return

        loaded = load_guild_settings(self.bot, server["guild"])
        if loaded is None:
            logging.error("Could not load guild settings for guild %s", server["guild"])
            return

        bypass_role: nextcord.Role | None = loaded["roles"]["bypass"]
        if bypass_role and member.get_role(bypass_role.id):
            # Guild has a valid bypass role and this user has it, skip
            return

        result: bool = await check_player_data(player, {str(member.guild.id): loaded})
        if result is False:
            print(f"Error updating player {player}, skipping...")
            return

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

        embed = nextcord.Embed(description=f"Pretending that <@{user.id}> just joined")
        await interaction.send(embed=embed)
        if interaction.user.get_role(1144720671558078485) is None:
            await interaction.send(
                "You do not have the Contributors role and cannot run this command.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(user.id)
        await self.new_member(member)

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
        await interaction.send("Running update loop for all guilds.")
        await self.update_rgl()
