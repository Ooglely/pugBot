"""Cog storing commands to manually add up to pugs."""
import time

import nextcord
from nextcord.ext import commands, tasks

from constants import BOT_COLOR
from database import BotCollection
from pug import BooleanView, FirstToSelect, ChannelSelect
from pug.pug import PugRunningCog
from registration import SetupIntroduction
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

    def __init__(self, bot: nextcord.Client):
        self.bot = bot
        self.status_check.start()  # pylint: disable=no-member

    @tasks.loop(minutes=1)
    async def status_check(self):
        """Check the status of all players added up."""
        print("Checking status")
        guilds = await guild_configs.find_all_items()
        for guild in guilds:
            changed: bool = False
            if "manual" not in guild:
                continue
            if not guild["manual"]["enabled"]:
                continue
            if len(guild["manual"]["players"]) == 0:
                continue
            current_time = round(time.time())
            for player in guild["manual"]["players"]:
                if current_time > player[1]:
                    changed = True
                    await guild_configs.update_item(
                        {"guild": guild["guild"]},
                        {"$pull": {"manual.players": player}},
                    )
            if changed:
                await self.update_channel_status(
                    self.bot.get_guild(guild["guild"]),
                    self.bot.get_channel(guild["manual"]["channel"]),
                )

    @status_check.error
    async def server_check_error_handler(self, exception: Exception):
        """Handles printing errors to console for the loop

        Args:
            exception (Exception): The exception that was raised
        """
        print("Error in manual status check loop:\n")
        print(exception.__class__.__name__)
        print(exception.__cause__)
        print(exception)

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

        setup_embed.add_field(
            name="Current Settings",
            value=f"Enabled: {settings['enabled']}\nChannel: <#{settings['channel']}>\nPlayers: {settings['num_players']}",
        )
        intro_view = SetupIntroduction()
        await interaction.send(embed=setup_embed, view=intro_view)
        await intro_view.wait()
        if intro_view.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        if intro_view.action == "disable":
            settings["enabled"] = False
            await update_guild_settings(interaction.guild.id, "manual", settings)
            return
        settings["enabled"] = True
        setup_embed.clear_fields()

        setup_embed.description = "Please select the channel you would like to have the pug's add up status displayed in and players to be pinged in."
        topic_channel_view = ChannelSelect()
        await interaction.edit_original_message(
            embed=setup_embed, view=topic_channel_view
        )
        await topic_channel_view.wait()
        if topic_channel_view.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        settings["channel"] = topic_channel_view.channel_id

        player_count_view = FirstToSelect()
        setup_embed.description = (
            "Please select the number of players you would like to add up to the pug."
        )
        await interaction.edit_original_message(
            embed=setup_embed, view=player_count_view
        )
        await player_count_view.wait()
        settings["num_players"] = player_count_view.num

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
        add_time: int
        | None = nextcord.SlashOption(
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
            print("Updating time")
            for player in guild_settings["manual"]["players"]:
                if player[0] == interaction.user.id:
                    old_time: int = player[1]
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

        await self.update_channel_status(
            interaction.guild, self.bot.get_channel(guild_settings["manual"]["channel"])
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
        guild_settings = await guild_configs.find_item({"guild": interaction.guild.id})
        player_ids: list[int] = [
            player[0] for player in guild_settings["manual"]["players"]
        ]
        if interaction.user.id not in player_ids:
            await interaction.send("You are not in the pug queue.")
            return
        for player in guild_settings["manual"]["players"]:
            if player[0] == interaction.user.id:
                old_time: int = player[1]
        await guild_configs.update_item(
            {"guild": interaction.guild.id},
            {"$pull": {"manual.players": [interaction.user.id, old_time]}},
        )
        await interaction.send("You have been removed from the pug queue.")
        await self.update_channel_status(
            interaction.guild, self.bot.get_channel(guild_settings["manual"]["channel"])
        )

    @manual_check()
    @nextcord.slash_command(name="status", description="Check the status of the pug.")
    async def queue_status(self, interaction: nextcord.Interaction):
        """Check the status of the pug.

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
            boolean_view = BooleanView()
            await interaction.send(
                "Are you sure you want to clear the pug queue?", view=boolean_view
            )
            await boolean_view.wait()
            if boolean_view.action:
                await guild_configs.update_item(
                    {"guild": interaction.guild.id}, {"$set": {"manual.players": []}}
                )
                await interaction.edit_original_message(
                    content="The pug queue has been cleared.", view=None
                )
                await self.update_channel_status(
                    interaction.guild,
                    self.bot.get_channel(guild_settings["manual"]["channel"]),
                )
            else:
                await interaction.edit_original_message(
                    content="The pug queue has not been cleared.", view=None
                )
        else:
            player_ids: list[int] = [
                player[0] for player in guild_settings["manual"]["players"]
            ]
            if interaction.user.id not in player_ids:
                await interaction.send("The user is not in the pug queue.")
                return
            for added_player in guild_settings["manual"]["players"]:
                if added_player[0] == interaction.user.id:
                    old_time: int = added_player[1]
            await guild_configs.update_item(
                {"guild": interaction.guild.id},
                {"$pull": {"manual.players": [interaction.user.id, old_time]}},
            )
            await interaction.send("The user has been removed from the pug queue.")
            await self.update_channel_status(
                interaction.guild,
                self.bot.get_channel(guild_settings["manual"]["channel"]),
            )

    async def update_channel_status(
        self, guild: nextcord.Guild, channel: nextcord.TextChannel
    ):
        """Update the channel status for the guild."""
        try:
            guild_settings = await guild_configs.find_item({"guild": guild.id})
            if "manual" not in guild_settings:
                return
        except LookupError:
            return

        if "roles" in guild_settings:
            guild_roles = guild_settings["roles"]
            sorted_roles = sorted(
                guild_roles.items(), key=lambda x: x[1]["value"], reverse=True
            )
        else:
            sorted_roles = []

        # Check if there are already enough players added up
        if (
            len(guild_settings["manual"]["players"])
            > guild_settings["manual"]["num_players"]
        ):
            return

        # Later add a check for the balance role the user has to add it to the string

        current_players = len(guild_settings["manual"]["players"])
        max_players: int = guild_settings["manual"]["num_players"]

        player_string: str = ""
        for player in guild_settings["manual"]["players"]:
            player_id = player[0]
            player_icon: str | None = None
            # Check for first role player has
            member = await guild.fetch_member(player_id)
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

        await channel.edit(
            topic=f"Add up using /add! | Pug queue: {current_players}/{max_players} | {player_string}"
        )

    @commands.Cog.listener("on_voice_state_update")
    async def voice_state_update(
        self,
        member: nextcord.Member,
        before: nextcord.VoiceState,
        after: nextcord.VoiceState,
    ):
        """Update the channel status for the guild.

        Args:
            member (nextcord.Member): The member who's voice state changed.
            before (nextcord.VoiceState): The voice state before the change.
            after (nextcord.VoiceState): The voice state after the change.
        """
        if before.channel == after.channel:
            return
        try:
            guild_settings = await guild_configs.find_item({"guild": member.guild.id})
            if "manual" not in guild_settings:
                return
        except LookupError:
            return

        # Check if there are enough players added up
        if (
            len(guild_settings["manual"]["players"])
            < guild_settings["manual"]["num_players"]
        ):
            return

        all_vc_members: list[int] = []
        for channel in member.guild.voice_channels:
            all_vc_members.extend([member.id for member in channel.members])
        players_added = list(
            set(all_vc_members)
            & set([player[0] for player in guild_settings["manual"]["players"]])
        )

        if len(players_added) == guild_settings["manual"]["num_players"]:
            await guild_configs.update_item(
                {"guild": member.guild.id}, {"$set": {"manual.players": []}}
            )
            await self.update_channel_status(
                member.guild, self.bot.get_channel(guild_settings["manual"]["channel"])
            )
