"""Cog storing commands to manually add up to pugs."""

import asyncio
import logging
import time
import traceback

import nextcord
from nextcord.ext import commands, tasks

from constants import BOT_COLOR
from database import BotCollection
from pug.pug import PugRunningCog
from menus import BotMenu
from menus.callbacks import action_callback, value_callback
from menus.templates import send_channel_prompt
from util import is_runner

guild_configs: BotCollection = BotCollection("guilds", "config")


async def update_guild_settings(guild: int, entry: str, settings: dict | int):
    """Update the guild settings in the database.

    Args:
        guild (int): The guild ID to update.
        settings (dict): The settings to update.
    """
    try:
        _guild_settings = await guild_configs.find_item({"guild": guild})
    except LookupError:
        return
    await guild_configs.update_item({"guild": guild}, {"$set": {entry: settings}})


def manual_check():
    """A decorator to check if the server has manual pugs enabled and setup."""

    async def predicate(interaction: nextcord.Interaction):
        if interaction.guild is None or not isinstance(
            interaction.guild, nextcord.Guild
        ):
            return
        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
        except LookupError:
            await interaction.send(
                "This server has not been setup yet. Please run /setup first."
            )
            return False

        if "manual" not in guild_settings:
            await interaction.send(
                "This server does not have manual pugs setup.\nRunners can run /pug manual setup to setup manual pugs."
            )
            return False

        if not guild_settings["manual"]["enabled"]:
            await interaction.send(
                "This server does not have manual pugs enabled.\nRunners can run /pug manual setup to setup manual pugs."
            )
            return False

        return True

    return nextcord.ext.application_checks.check(predicate)


class ManualPugCog(commands.Cog):
    """Cog storing commands to manually add up to pugs."""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @tasks.loop(minutes=1)
    async def status_check(self):
        """Check the status of all players added up."""
        print("Checking status")
        guilds = await guild_configs.find_all_items()
        for guild in guilds:
            if "manual" not in guild:
                continue
            if not guild["manual"]["enabled"]:
                continue
            if len(guild["manual"]["players"]) == 0:
                continue
            current_time = round(time.time())
            for player in guild["manual"]["players"]:
                if current_time > player[1]:
                    await guild_configs.update_item(
                        {"guild": guild["guild"]},
                        {"$pull": {"manual.players": player}},
                    )

    @tasks.loop()
    async def update_channel_status(self):
        """Update the channel status for the guild."""
        print("Updating channel statuses")
        guilds = await guild_configs.find_all_items()
        for guild in guilds:
            if "manual" not in guild:
                continue
            if not guild["manual"]["enabled"]:
                continue

            if "roles" in guild:
                guild_roles = guild["roles"]
                sorted_roles = sorted(
                    guild_roles.items(), key=lambda x: x[1]["value"], reverse=True
                )
            else:
                sorted_roles = []

            # Check if there are already enough players added up
            if len(guild["manual"]["players"]) > guild["manual"]["num_players"]:
                return

            current_players = len(guild["manual"]["players"])
            max_players: int = guild["manual"]["num_players"]
            guild_obj: nextcord.Guild = self.bot.get_guild(int(guild["guild"]))
            if guild_obj is None:
                continue
            channel: nextcord.TextChannel = guild_obj.get_channel(
                guild["manual"]["channel"]
            )

            if channel is None:
                continue
            permissions = channel.permissions_for(guild_obj.me)
            if not permissions.manage_channels:
                logging.warning(
                    "Missing permissions to edit channel topic in guild: %s", guild
                )
                continue

            player_string: str = ""
            for player in guild["manual"]["players"]:
                player_id = player[0]
                player_icon: str | None = None
                # Check for first role player has
                member = await guild_obj.fetch_member(player_id)
                if sorted_roles != []:
                    for role in sorted_roles:
                        if int(role[0]) in [role.id for role in member.roles]:
                            player_icon = role[1]["icon"]
                            break
                if player_icon is None:
                    player_string += f"<@{player_id}>, "
                else:
                    player_string += f"{player_icon} <@{player_id}>, "

            if player_string != "":
                player_string = player_string[:-2]
            try:
                await channel.edit(
                    topic=f"Add up using /add! | Pug queue: {current_players}/{max_players} | {player_string}"
                )
            except nextcord.errors.Forbidden:
                print("Missing permissions to edit channel topic.\nGuild: ", guild)
            except nextcord.HTTPException:
                print(
                    "HTTP Exception when editing channel topic. Likely inappropriate username.\nGuild: ",
                    guild,
                )
            await asyncio.sleep(360)

    @status_check.error
    @update_channel_status.error
    async def server_check_error_handler(self, _exception: Exception):
        """Handles printing errors to console for the loop

        Args:
            exception (Exception): The exception that was raised
        """
        print("Error in manual status check loop:\n")
        print(traceback.format_exc())

    @PugRunningCog.pug.subcommand(name="manual")  # pylint: disable=no-member
    async def manual_group(self, interaction: nextcord.Interaction):
        """
        /pug manual subcommand group.
        """

    @is_runner()
    @manual_group.subcommand(
        name="setup", description="Setup guild settings for manual pugs."
    )
    async def manual_setup(
        self,
        interaction: nextcord.Interaction,
    ):
        """Setup guild settings for manual pugs.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

        setup_embed = nextcord.Embed(
            title="Manual Pugs Setup",
            color=BOT_COLOR,
        )
        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
            print(guild_settings)
        except LookupError:
            await interaction.send(
                "This server has not been setup yet. Please run /setup first."
            )
            return

        if "manual" in guild_settings:
            settings = guild_settings["manual"]
        else:
            settings = {
                "enabled": False,
                "channel": 0,
                "num_players": 0,
                "players": [],
            }

        menu: BotMenu = BotMenu(embed=setup_embed, user_id=interaction.user.id)
        if menu.embed is None:
            return
        menu.embed.add_field(
            name="Current Settings",
            value=f"Enabled: {settings['enabled']}\nChannel: <#{settings['channel']}>\nPlayers: {settings['num_players']}",
        )
        menu.add_button(
            "Enable and Setup",
            await action_callback("enable", interaction.user.id),
            nextcord.ButtonStyle.green,
        )
        menu.add_button(
            "Disable",
            await action_callback("disable", interaction.user.id),
            nextcord.ButtonStyle.red,
        )
        menu.add_button(
            "Cancel",
            await action_callback("cancel", interaction.user.id),
            nextcord.ButtonStyle.gray,
        )
        await menu.send(interaction)
        if not await menu.wait_for_action(self.bot) or menu.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        if menu.action == "disable":
            settings["enabled"] = False
            await update_guild_settings(interaction.guild.id, "manual", settings)
            return
        settings["enabled"] = True
        menu.embed.clear_fields()

        menu.embed.description = "Please select the channel you would like to have the pug's add up status displayed in and players to be pinged in."
        menu.clear_items()
        await menu.add_continue_buttons()
        try:
            channels: list[nextcord.TextChannel] = await send_channel_prompt(
                menu, interaction, ["Status Channel"], True, [nextcord.ChannelType.text]
            )
        except TimeoutError:
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        except ValueError:
            await interaction.edit_original_message(
                content="No channel selected. Please try again."
            )
            await interaction.delete_original_message(delay=10)
            return
        settings["channel"] = channels[0].id

        menu.embed.description = "Please select the number of players / team size that you would like for the queue."
        menu.clear_items()
        menu.add_button(
            "Ultiduo (4)", await value_callback("num", 4, interaction.user.id)
        )
        menu.add_button(
            "Ultitrio (6)", await value_callback("num", 6, interaction.user.id)
        )
        menu.add_button(
            "Passtime (8)", await value_callback("num", 8, interaction.user.id)
        )
        menu.add_button("6s (12)", await value_callback("num", 12, interaction.user.id))
        menu.add_button(
            "Highlander (18)", await value_callback("num", 18, interaction.user.id)
        )
        await menu.edit(interaction)
        if not await menu.wait_for_action(self.bot):
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        try:
            settings["num_players"] = menu.values["num"]
        except KeyError:
            await interaction.edit_original_message(
                content="No number selected. Please try again.", view=None
            )
            await interaction.delete_original_message(delay=10)
            return

        setup_embed.description = f"Manual pugs have been setup.\nEnabled: {settings['enabled']}\nChannel: <#{settings['channel']}>\nPlayers: {settings['num_players']}"
        setup_embed.add_field(
            name="Commands for players", value="/add, /remove, /status"
        )
        setup_embed.add_field(name="Commands for runners", value="/missing, /clear")
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=60)
        await update_guild_settings(interaction.guild.id, "manual", settings)

    @is_runner()
    @manual_check()
    @manual_group.subcommand(
        name="default", description="Setup default add time for manual pugs."
    )
    async def default_add_time(
        self,
        interaction: nextcord.Interaction,
        hours: int = nextcord.SlashOption(
            name="hours",
            description="The default hours to add up for.",
            required=True,
        ),
    ):
        """Setup default add time for manual pugs.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            hours (int): The default hours to add up for.
        """
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
            print(guild_settings)
        except LookupError:
            await interaction.send(
                "This server has not been setup yet. Please run /setup first."
            )
            return

        await update_guild_settings(interaction.guild.id, "manual.default", hours)
        await interaction.send(f"Default add time has been set to {hours} hours.")

    @manual_check()
    @nextcord.slash_command(
        name="add", description="Add yourself from the add up list."
    )
    async def manual_add(
        self,
        interaction: nextcord.Interaction,
        add_time: int | None = nextcord.SlashOption(
            name="time",
            description="The hours to add up for.",
            required=False,
            default=None,
            max_value=12,
            min_value=1,
        ),
    ):
        """Manually add up to a pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            time (int, optional): The hours to add up for. Defaults to 2.
        """
        await interaction.response.defer()
        guild_settings = await guild_configs.find_item({"guild": interaction.guild.id})
        if add_time is None:
            if "default" not in guild_settings["manual"]:
                add_time = 4
            else:
                add_time = guild_settings["manual"]["default"]

        removal_time: int = round(time.time()) + (add_time * 3600)

        if interaction.user.id in [
            player[0] for player in guild_settings["manual"]["players"]
        ]:
            # Update the time for the player
            old_time: int = -1
            for player in guild_settings["manual"]["players"]:
                if player[0] == interaction.user.id:
                    old_time = player[1]
            if old_time == -1:
                await interaction.send(
                    "Unable to find player even though first check was passed. Please report this to the pugBot support server."
                )
                return
            # Pull any instances of the player
            await guild_configs.update_item(
                {"guild": interaction.guild.id},
                {"$pull": {"manual.players": [interaction.user.id, old_time]}},
            )
            await guild_configs.update_item(
                {"guild": interaction.guild.id},
                {"$push": {"manual.players": [interaction.user.id, removal_time]}},
            )
            await interaction.send(f"Updated your time to {add_time} hours.")
            return

        current_players = len(guild_settings["manual"]["players"]) + 1
        max_players: int = guild_settings["manual"]["num_players"]

        if current_players > max_players:
            await interaction.send(
                "The max amount of players have already added up.\nPlease wait for a runner to clear the queue."
            )
            return

        # Add player to list
        await guild_configs.update_item(
            {"guild": interaction.guild.id},
            {"$push": {"manual.players": [interaction.user.id, removal_time]}},
        )

        await interaction.send(
            f"{interaction.user.mention} has added up for {add_time} hours.\nNow at {current_players}/{max_players} players."
        )

        if current_players == max_players:
            player_ids: list[int] = [
                player[0] for player in guild_settings["manual"]["players"]
            ]
            player_ids.append(interaction.user.id)
            player_mentions: str = " ".join([f"<@{player}>" for player in player_ids])
            pug_embed = nextcord.Embed(
                title="Pug started!",
                description="Please join the voice channels to pug.",
                color=BOT_COLOR,
            )
            await self.bot.get_channel(guild_settings["manual"]["channel"]).send(
                player_mentions, embed=pug_embed
            )

    @manual_check()
    @nextcord.slash_command(
        name="remove", description="Remove yourself from the pug queue."
    )
    async def manual_remove(self, interaction: nextcord.Interaction):
        """Manually remove yourself from a pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        await interaction.response.defer()
        guild_settings = await guild_configs.find_item({"guild": interaction.guild.id})
        player_ids: list[int] = [
            player[0] for player in guild_settings["manual"]["players"]
        ]
        if interaction.user.id not in player_ids:
            await interaction.send("You are not in the pug queue.")
            return
        old_time: int = -1
        for player in guild_settings["manual"]["players"]:
            if player[0] == interaction.user.id:
                old_time = player[1]
        if old_time == -1:
            await interaction.send(
                "Unable to find player even though first check was passed. Please report this to the pugBot support server."
            )
            return
        await guild_configs.update_item(
            {"guild": interaction.guild.id},
            {"$pull": {"manual.players": [interaction.user.id, old_time]}},
        )
        await interaction.send("You have been removed from the pug queue.")

    @manual_check()
    @nextcord.slash_command(name="status", description="Check the status of the pug.")
    async def queue_status(self, interaction: nextcord.Interaction):
        """Check the status of the pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        await interaction.response.defer()
        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
            if "manual" not in guild_settings:
                return
        except LookupError:
            return

        current_players = len(guild_settings["manual"]["players"])
        max_players: int = guild_settings["manual"]["num_players"]
        player_ids: list[list[int]] = list(guild_settings["manual"]["players"])

        player_string: str = "\n".join([f"<@{player[0]}>" for player in player_ids])
        time_string: str = "\n".join([f"<t:{player[1]}:R>" for player in player_ids])

        queue_embed = nextcord.Embed(
            title="Pug Queue",
            color=BOT_COLOR,
        )
        queue_embed.add_field(
            name=f"Players | {current_players}/{max_players}", value=player_string
        )
        queue_embed.add_field(name="Time", value=time_string)
        await interaction.send(embed=queue_embed)

    @manual_check()
    @is_runner()
    @nextcord.slash_command(
        name="missing", description="Check who is missing from the pug."
    )
    async def missing_status(self, interaction: nextcord.Interaction):
        """Check who is missing from the pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
            if "manual" not in guild_settings:
                return
        except LookupError:
            return

        current_players = len(guild_settings["manual"]["players"])
        max_players: int = guild_settings["manual"]["num_players"]

        if current_players == max_players:
            all_vc_members: list[int] = []
            for channel in interaction.guild.voice_channels:
                all_vc_members.extend([member.id for member in channel.members])

            all_queue_members: set[int] = set(
                [player[0] for player in guild_settings["manual"]["players"]]
            )

            missing_players = [i for i in all_queue_members if i not in all_vc_members]
            await interaction.send(
                f"Missing players: {' '.join([f'<@{player}>' for player in missing_players])}"
            )
        else:
            await interaction.send("The pug queue is not full yet.")
            return

    @manual_check()
    @is_runner()
    @nextcord.slash_command(
        name="clear", description="Clear a player or all players from the pug queue."
    )
    async def clear_player(
        self, interaction: nextcord.Interaction, player: nextcord.Member = None
    ):
        """Clear a player or all players from the pug queue.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        guild_settings = await guild_configs.find_item({"guild": interaction.guild.id})
        if player is None:
            menu: BotMenu = BotMenu(interaction.user.id)
            menu.add_button("Yes", await action_callback("clear", interaction.user.id))
            menu.add_button("No", await action_callback("cancel", interaction.user.id))
            menu.embed = nextcord.Embed(
                title="Clear Pug Queue",
                description="Are you sure you want to clear the pug queue?",
                color=BOT_COLOR,
            )
            await menu.send(interaction)
            if not await menu.wait_for_action(self.bot):
                await interaction.delete_original_message(delay=1)
                return
            if menu.action == "clear":
                await guild_configs.update_item(
                    {"guild": interaction.guild.id}, {"$set": {"manual.players": []}}
                )
                menu.embed.description = "The pug queue has been cleared."
                await interaction.edit_original_message(embed=menu.embed, view=None)
            else:
                menu.embed.description = "The pug queue has not been cleared."
                await interaction.edit_original_message(embed=menu.embed, view=None)
        else:
            player_ids: list[int] = [
                player[0] for player in guild_settings["manual"]["players"]
            ]
            if player.id not in player_ids:
                await interaction.send("The user is not in the pug queue.")
                return
            old_time: int = -1
            for added_player in guild_settings["manual"]["players"]:
                if added_player[0] == player.id:
                    old_time = added_player[1]
            if old_time == -1:
                await interaction.send(
                    "Unable to find player even though first check was passed. Please report this to the pugBot support server."
                )
                return
            await guild_configs.update_item(
                {"guild": interaction.guild.id},
                {"$pull": {"manual.players": [player.id, old_time]}},
            )
            await interaction.send("The user has been removed from the pug queue.")
