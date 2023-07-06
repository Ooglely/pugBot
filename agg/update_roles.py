"""Contains the cog to update users roles over time."""
import asyncio
import nextcord
from nextcord.ext import tasks, commands

import agg
import database as db

from rgl_api import RGL_API

RGL: RGL_API = RGL_API()


class UpdateRolesCog(commands.Cog):
    """Contains the cog to update users roles over time."""

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.update_rgl.start()  # pylint: disable=no-member

    @tasks.loop(hours=24)  # time=update_time
    async def update_rgl(self):
        """Updates RGL divisions and roles for all registered players"""
        print("Updating RGL divisions and roles for all registered players...")
        players = db.get_all_players()
        for player in players:
            await asyncio.sleep(5)
            print(player)
            agg_server: nextcord.Guild = self.bot.get_guild(agg.AGG_SERVER_ID[0])

            discord_user: nextcord.Member = agg_server.get_member(
                int(player["discord"])
            )

            div_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
                1060023899666002001
            )
            ban_appeal_channel: nextcord.TextChannel = agg_server.get_channel(
                1006534381998981140
            )
            log_channel: nextcord.TextChannel = agg_server.get_channel(
                1026985050677465148
            )

            nc_am_role: nextcord.Role = agg_server.get_role(992286429881303101)
            im_role: nextcord.Role = agg_server.get_role(992281832437596180)
            main_role: nextcord.Role = agg_server.get_role(1117852769823502397)
            ad_in_role: nextcord.Role = agg_server.get_role(1060021145212047391)

            hl_div_ban: nextcord.Role = agg_server.get_role(1060020104462606396)
            ban_role: nextcord.Role = agg_server.get_role(997607002299707432)

            try:
                await RGL.get_player(int(player["steam"]))
            except LookupError:
                print(f"Player {player['discord']} not found in RGL, skipping...")
                continue

            await asyncio.sleep(5)

            try:
                player_divs = await RGL.get_div_data(int(player["steam"]))
            except LookupError:
                print("Rate limited by RGL API, skipping...")
                continue
            top_div = player_divs["hl"]["highest"]
            print(top_div)

            if top_div == -1:
                print(
                    f"RGL api timed out while searching player {player['discord']}, skipping..."
                )
                continue

            await db.update_divisons(player["steam"], player_divs)

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

                db_player = db.get_player_from_steam(player["steam"])
                if "rgl_ban" in db_player:
                    old_ban_status = db_player["rgl_ban"]
                else:
                    old_ban_status = False
                new_ban_status = await db.update_rgl_ban_status(int(player["steam"]))
                if (old_ban_status is False) and (new_ban_status is True):
                    await discord_user.add_roles(ban_role)
                    await ban_appeal_channel.send(
                        f"<@{player['discord']}> You have been automatically banned from pugs due to currently being RGL banned."
                    )

                if (old_ban_status is True) and (new_ban_status is False):
                    await log_channel.send(
                        f"<@{player['discord']}> is no longer banned on RGL."
                    )
