"""Contains the cog to update users roles over time."""
import datetime

import asyncio
import nextcord
from nextcord.ext import tasks, commands

import agg
import database as db
from constants import BOT_COLOR
from registration import RegistrationSettings
from rgl_api import RGL_API

RGL: RGL_API = RGL_API()

update_time = datetime.time(hour=6, minute=0, tzinfo=datetime.timezone.utc)


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member

    @tasks.loop(time=update_time)  # time=update_time
    async def update_rgl(self):
        """Updates RGL divisions and roles for all registered players"""
        print("Updating RGL divisions and roles for all registered players...")
        players = db.get_all_players()
        all_players = []
        server_cursor = db.get_all_servers()
        all_servers = []
        for server in server_cursor:
            all_servers.append(server)
        for player in players:
            # Does this suck? Yes. But mongoDB cursors time out after a while
            all_players.append(player)
        for player in all_players:
            await asyncio.sleep(20)
            print(player)
            steam_id = int(player["steam"])
            discord_id = int(player["discord"])
            try:
                player_divs = await RGL.get_div_data(int(player["steam"]))
            except LookupError:
                print("Rate limited by RGL API, skipping...")
                await asyncio.sleep(30)
                continue
            print(player_divs)
            await asyncio.sleep(3)
            old_ban: bool
            if "rgl_ban" in player:
                old_ban = player["rgl_ban"]
            else:
                old_ban = False
            print(old_ban)
            # Trying to prevent rate limiting
            try:
                new_ban = await RGL.check_banned(steam_id)
            except LookupError:
                print("Not able to check if player is banned, using old ban status...")
                new_ban = old_ban
                await asyncio.sleep(30)
            print(new_ban)
            if player_divs["hl"]["highest"] == -1:
                print(
                    f"RGL API timed out while updating player {player['discord']}, skipping..."
                )
                continue
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
                print(server)
                # AGG specific registration checks
                if server["guild"] == 952817189893865482:
                    await self.agg_update_roles(player, player_divs, old_ban, new_ban)
                    continue

                reg_settings = RegistrationSettings()
                reg_settings.import_from_db(server["guild"])

                gamemode: str
                if reg_settings.gamemode == "sixes":
                    gamemode = "sixes"
                elif reg_settings.gamemode == "highlander":
                    gamemode = "hl"

                division = player_divs[gamemode][reg_settings.mode]
                old_divison: int
                if "divison" not in player:
                    old_divison = 0
                else:
                    try:
                        old_divison = player["divison"][gamemode][reg_settings.mode]
                    except TypeError:
                        old_divison = player["divison"][gamemode]

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

                logs_channel: nextcord.TextChannel = guild.get_channel(
                    reg_settings.channels["logs"]
                )

                member: nextcord.Member = guild.get_member(discord_id)

                # Do not update roles if player has bypass role
                if reg_settings.bypass and reg_settings.roles["bypass"] is not None:
                    if member.get_role(reg_settings.roles["bypass"]) is not None:
                        continue

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

                # If the player has no division role at all, we want to update as well
                matching_roles = [i for i in divison_roles if i in member.roles]
                if matching_roles == []:
                    print("Adding role...")
                    await member.add_roles(divison_roles[division])
                    log_embed = nextcord.Embed(
                        title="Updated Division",
                        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                        + str(steam_id),
                        color=BOT_COLOR,
                    )
                    log_embed.add_field(
                        name="Discord", value=f"<@{discord_id}>", inline=True
                    )
                    log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                    log_embed.add_field(
                        name="Roles Added",
                        value=f"<@&{divison_roles[division].id}>",
                        inline=False,
                    )
                    log_embed.add_field(
                        name="Roles Removed",
                        value="None",
                        inline=True,
                    )

                    await logs_channel.send(embed=log_embed)

                if old_divison != division:
                    print("Updating roles...")
                    await member.remove_roles(
                        nc_role, am_role, im_role, main_role, adv_role, inv_role
                    )
                    await member.add_roles(divison_roles[division])
                    log_embed = nextcord.Embed(
                        title="Updated Division",
                        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                        + str(steam_id),
                        color=BOT_COLOR,
                    )
                    log_embed.add_field(
                        name="Discord", value=f"<@{discord_id}>", inline=True
                    )
                    log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                    log_embed.add_field(
                        name="Roles Added",
                        value=f"<@&{divison_roles[division].id}>",
                        inline=False,
                    )
                    log_embed.add_field(
                        name="Roles Removed",
                        value=f"<@&{divison_roles[old_divison].id}>",
                        inline=True,
                    )

                    await logs_channel.send(embed=log_embed)

                if reg_settings.ban:
                    if (old_ban is False) and (new_ban is True):
                        await member.add_roles(ban_role)
                        ban_embed = nextcord.Embed(
                            title="RGL Banned Player",
                            url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                            + str(steam_id),
                            color=BOT_COLOR,
                        )
                        ban_embed.add_field(
                            name="Discord", value=f"<@{discord_id}>", inline=True
                        )
                        ban_embed.add_field(
                            name="Steam", value=str(steam_id), inline=True
                        )
                        ban_embed.add_field(
                            name="Roles Added",
                            value=f"<@&{ban_role.id}>",
                            inline=False,
                        )
                        await logs_channel.send(embed=ban_embed)

                    if (old_ban is True) and (new_ban is False):
                        await member.remove_roles(ban_role)
                        ban_embed = nextcord.Embed(
                            title="RGL Unbanned Player",
                            url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                            + str(steam_id),
                            color=BOT_COLOR,
                        )
                        ban_embed.add_field(
                            name="Discord", value=f"<@{discord_id}>", inline=True
                        )
                        ban_embed.add_field(
                            name="Steam", value=str(steam_id), inline=True
                        )
                        ban_embed.add_field(
                            name="Roles Removed",
                            value=f"<@&{ban_role.id}>",
                            inline=False,
                        )
                        await logs_channel.send(embed=ban_embed)
            print(f"Finished updating roles for {discord_id}")
            print(player_divs)
            await db.update_divisons(steam_id, player_divs)
            await db.update_rgl_ban_status(steam_id)
        print("Finished updating roles for all players")

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

    async def agg_update_roles(self, player, player_divs, old_ban, new_ban):
        """AGG role update function

        Args:
            player (_type_): _description_
        """
        agg_server: nextcord.Guild = self.bot.get_guild(agg.AGG_SERVER_ID[0])

        discord_user: nextcord.Member = agg_server.get_member(int(player["discord"]))

        div_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
            1060023899666002001
        )
        ban_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
            1006534381998981140
        )
        log_channel: nextcord.TextChannel = agg_server.get_channel(1026985050677465148)

        nc_am_role: nextcord.Role = agg_server.get_role(992286429881303101)
        im_role: nextcord.Role = agg_server.get_role(992281832437596180)
        main_role: nextcord.Role = agg_server.get_role(1117852769823502397)
        ad_in_role: nextcord.Role = agg_server.get_role(1060021145212047391)

        hl_div_ban: nextcord.Role = agg_server.get_role(1060020104462606396)
        ban_role: nextcord.Role = agg_server.get_role(997607002299707432)

        await asyncio.sleep(5)

        top_div = player_divs["hl"]["highest"]
        print(top_div)

        if top_div == -1:
            print(
                f"RGL api timed out while searching player {player['discord']}, skipping..."
            )
            return

        if discord_user is not None:
            if top_div >= 5:  # Advanced+
                await discord_user.add_roles(ad_in_role)
                lower_roles = [nc_am_role, im_role, main_role]
                matching_roles = [i for i in lower_roles if i in discord_user.roles]
                print(matching_roles)
                if matching_roles != []:
                    await discord_user.remove_roles(nc_am_role, im_role, main_role)
                    await div_appeal_channel.send(
                        f"<@{player['discord']}> You have been automatically restricted from pugs due to having Advanced/Invite experience in Highlander or 6s.\nIf you believe that you should be let in (for example, you roster rode on your Advanced seasons or you've played in here before), please let us know."
                    )
                    if top_div >= 5:
                        await discord_user.add_roles(hl_div_ban)

            elif top_div >= 4:  # Main+
                await discord_user.add_roles(main_role)
                await discord_user.remove_roles(nc_am_role, im_role)
            elif top_div >= 3:  # IM+
                await discord_user.add_roles(im_role)
                await discord_user.remove_roles(nc_am_role)
            else:  # NC-AM
                await discord_user.add_roles(nc_am_role)

            if (old_ban is False) and (new_ban is True):
                await discord_user.add_roles(ban_role)
                await ban_appeal_channel.send(
                    f"<@{player['discord']}> You have been automatically banned from pugs due to currently being RGL banned."
                )

            if (old_ban is True) and (new_ban is False):
                await discord_user.remove_roles(ban_role)
                await log_channel.send(
                    f"<@{player['discord']}> is no longer banned on RGL."
                )

    @nextcord.slash_command(
        name="updateall",
        description="Updates RGL divisions and roles for all registered players in this server.",
        default_member_permissions=nextcord.Permissions(manage_guild=True),
    )
    async def update_guild_roles(self, interaction: nextcord.Interaction):
        """Updates RGL divisions and roles for all registered players"""
        await interaction.send(
            "Updating RGL divisions and roles for all registered players in this server.\nThis will take a while."
        )
        print("Updating players in guild " + str(interaction.guild_id))
        players = db.get_all_players()
        server = db.get_server(interaction.guild_id)
        for player in players:
            await asyncio.sleep(10)
            print(player)
            steam_id = int(player["steam"])
            discord_id = int(player["discord"])
            try:
                player_divs = await RGL.get_div_data(int(player["steam"]))
            except LookupError:
                print("Rate limited by RGL API, skipping...")
                await asyncio.sleep(30)
                continue
            old_ban: bool
            if "rgl_ban" in player:
                old_ban = player["rgl_ban"]
            else:
                old_ban = False
            new_ban = await db.update_rgl_ban_status(steam_id)
            if player_divs["hl"]["highest"] == -1:
                print(
                    f"RGL API timed out while updating player {player['discord']}, skipping..."
                )
                continue

            # If registration settings are not set up, skip
            if "registration" not in server:
                continue
            # If registration is disabled, skip
            if not server["registration"]["enabled"]:
                continue
            guild = self.bot.get_guild(server["guild"])
            # If member is not in server, skip
            if guild.get_member(discord_id) is None:
                continue
            # AGG specific registration checks
            if server["guild"] == 952817189893865482:
                await self.agg_update_roles(player, player_divs, old_ban, new_ban)
                continue

            reg_settings = RegistrationSettings()
            reg_settings.import_from_db(server["guild"])

            gamemode: str
            if reg_settings.gamemode == "sixes":
                gamemode = "sixes"
            elif reg_settings.gamemode == "highlander":
                gamemode = "hl"

            division = player_divs[gamemode][reg_settings.mode]
            old_divison = player["divison"][gamemode][reg_settings.mode]

            no_exp_role: nextcord.Role = guild.get_role(reg_settings.roles["noexp"])
            nc_role: nextcord.Role = guild.get_role(reg_settings.roles["newcomer"])
            am_role: nextcord.Role = guild.get_role(reg_settings.roles["amateur"])
            im_role: nextcord.Role = guild.get_role(reg_settings.roles["intermediate"])
            main_role: nextcord.Role = guild.get_role(reg_settings.roles["main"])
            adv_role: nextcord.Role = guild.get_role(reg_settings.roles["advanced"])
            inv_role: nextcord.Role = guild.get_role(reg_settings.roles["invite"])
            ban_role: nextcord.Role = guild.get_role(reg_settings.roles["ban"])

            logs_channel: nextcord.TextChannel = guild.get_channel(
                reg_settings.channels["logs"]
            )

            member: nextcord.Member = guild.get_member(discord_id)

            # Do not update roles if player has bypass role
            if reg_settings.bypass and reg_settings.roles["bypass"] is not None:
                if member.get_role(reg_settings.roles["bypass"]) is not None:
                    continue

            # Yes the double adv_role is intentional...
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

            # If the player has no division role at all, we want to update as well
            matching_roles = [i for i in divison_roles if i in member.roles]
            if matching_roles == []:
                await member.add_roles(divison_roles[division])
                log_embed = nextcord.Embed(
                    title="Updated Division",
                    url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
                    color=BOT_COLOR,
                )
                log_embed.add_field(
                    name="Discord", value=f"<@{discord_id}>", inline=True
                )
                log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                log_embed.add_field(
                    name="Roles Added",
                    value=f"<@&{divison_roles[division].id}>",
                    inline=False,
                )
                log_embed.add_field(
                    name="Roles Removed",
                    value="None",
                    inline=True,
                )

                await logs_channel.send(embed=log_embed)

            if old_divison != division:
                await member.remove_roles(divison_roles)
                await member.add_roles(divison_roles[division])
                log_embed = nextcord.Embed(
                    title="Updated Division",
                    url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(steam_id),
                    color=BOT_COLOR,
                )
                log_embed.add_field(
                    name="Discord", value=f"<@{discord_id}>", inline=True
                )
                log_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                log_embed.add_field(
                    name="Roles Added",
                    value=f"<@&{divison_roles[division].id}>",
                    inline=False,
                )
                log_embed.add_field(
                    name="Roles Removed",
                    value=f"<@&{divison_roles[old_divison].id}>",
                    inline=True,
                )

                await logs_channel.send(embed=log_embed)

            if reg_settings.ban:
                if (old_ban is False) and (new_ban is True):
                    await member.add_roles(ban_role)
                    ban_embed = nextcord.Embed(
                        title="RGL Banned Player",
                        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                        + str(steam_id),
                        color=BOT_COLOR,
                    )
                    ban_embed.add_field(
                        name="Discord", value=f"<@{discord_id}>", inline=True
                    )
                    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                    ban_embed.add_field(
                        name="Roles Added",
                        value=f"<@&{ban_role.id}>",
                        inline=False,
                    )
                    await logs_channel.send(embed=ban_embed)

                if (old_ban is True) and (new_ban is False):
                    await member.remove_roles(ban_role)
                    ban_embed = nextcord.Embed(
                        title="RGL Unbanned Player",
                        url="https://rgl.gg/Public/PlayerProfile.aspx?p="
                        + str(steam_id),
                        color=BOT_COLOR,
                    )
                    ban_embed.add_field(
                        name="Discord", value=f"<@{discord_id}>", inline=True
                    )
                    ban_embed.add_field(name="Steam", value=str(steam_id), inline=True)
                    ban_embed.add_field(
                        name="Roles Removed",
                        value=f"<@&{ban_role.id}>",
                        inline=False,
                    )
                    await logs_channel.send(embed=ban_embed)
            print(f"Finished updating roles for {discord_id}")
            print(player_divs)

    @commands.Cog.listener("on_member_join")
    async def new_member(self, member: nextcord.Member):
        """ASsigns roles to new members of a server if they are registered."""
        server = db.get_server(member.guild.id)
        try:
            player = db.get_player_from_discord(member.id)
        except LookupError:
            return

        # If registration settings are not set up, skip
        if "registration" not in server:
            return
        # If registration is disabled, skip
        if not server["registration"]["enabled"]:
            return

        guild = member.guild

        reg_settings = RegistrationSettings()
        reg_settings.import_from_db(member.guild.id)

        gamemode: str
        if reg_settings.gamemode == "sixes":
            gamemode = "sixes"
        elif reg_settings.gamemode == "highlander":
            gamemode = "hl"

        division = player["divison"][gamemode][reg_settings.mode]

        no_exp_role: nextcord.Role = guild.get_role(reg_settings.roles["noexp"])
        nc_role: nextcord.Role = guild.get_role(reg_settings.roles["newcomer"])
        am_role: nextcord.Role = guild.get_role(reg_settings.roles["amateur"])
        im_role: nextcord.Role = guild.get_role(reg_settings.roles["intermediate"])
        main_role: nextcord.Role = guild.get_role(reg_settings.roles["main"])
        adv_role: nextcord.Role = guild.get_role(reg_settings.roles["advanced"])
        inv_role: nextcord.Role = guild.get_role(reg_settings.roles["invite"])
        ban_role: nextcord.Role = guild.get_role(reg_settings.roles["ban"])

        logs_channel: nextcord.TextChannel = guild.get_channel(
            reg_settings.channels["logs"]
        )

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

        await member.add_roles(divison_roles[division])
        log_embed = nextcord.Embed(
            title="New Member",
            url="https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(player["steam"]),
            color=BOT_COLOR,
        )
        log_embed.add_field(
            name="Discord", value=f"<@{player['discord']}>", inline=True
        )
        log_embed.add_field(name="Steam", value=str(player["steam"]), inline=True)

        if reg_settings.ban and player["rgl_ban"]:
            await member.add_roles(ban_role)
            log_embed.add_field(
                name="Roles Added",
                value=f"<@&{ban_role.id}>",
                inline=False,
            )
        else:
            log_embed.add_field(
                name="Roles Added",
                value=f"<@&{divison_roles[division].id}>",
                inline=False,
            )

        await logs_channel.send(embed=log_embed)
