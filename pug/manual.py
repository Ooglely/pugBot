"""Cog storing commands to manually add up to pugs."""
from typing import Optional

import nextcord
from nextcord.ext import commands, tasks

from constants import BOT_COLOR
from database import BotCollection
from pug import BooleanView, FirstToSelect, ChannelSelect
from pug.pug import PugRunningCog
from registration import SetupIntroduction

guild_configs = BotCollection("guilds", "config")


async def update_guild_settings(guild: int, entry: str, settings: dict):
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
            return False

        if "manual" not in guild_settings:
            return False

        if not guild_settings["manual"]["enabled"]:
            return False

        return True

    return nextcord.ext.application_checks.check(predicate)


class ManualPugCog(commands.Cog):
    """Cog storing commands to manually add up to pugs."""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @tasks.loop(minutes=1)
    async def status_check(self):
        """Check the status of all players added up."""

    @PugRunningCog.pug.subcommand(name="manual")  # pylint: disable=no-member
    async def manual_group(self, interaction: nextcord.Interaction):
        """
        /pug manual subcommand group.
        """

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
                "players": 0,
            }

        setup_embed.add_field(
            name="Current Settings",
            value=f"Enabled: {settings['enabled']}\nChannel: <#{settings['channel']}>\nPlayers: {settings['players']}",
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

        topic_boolean_view = BooleanView()
        setup_embed.description = "Would you like to have the pug's add up status displayed in a channel's topic/status? (The text next to the channel name)"
        await interaction.edit_original_message(
            embed=setup_embed, view=topic_boolean_view
        )
        await topic_boolean_view.wait()
        if topic_boolean_view.action is False:
            settings["channel"] = None
        else:
            setup_embed.description = "Please select the channel you would like to have the pug's add up status displayed in."
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
        settings["players"] = player_count_view.num

        setup_embed.description = f"Manual pugs have been setup.\nEnabled: {settings['enabled']}\nChannel: <#{settings['channel']}>\nPlayers: {settings['players']}"
        setup_embed.add_field(
            name="Commands for players", value="/add, /remove, /status"
        )
        setup_embed.add_field(name="Commands for runners", value="/missing, /clear")
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=60)
        await update_guild_settings(interaction.guild.id, "manual", settings)

    @nextcord.slash_command(
        name="add", description="Add yourself from the add up list."
    )
    async def manual_add(
        self,
        interaction: nextcord.Interaction,
        time: Optional[int] = nextcord.SlashOption(
            name="time",
            description="The hours to add up for.",
            required=False,
            default=2,
        ),
    ):
        """Manually add up to a pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            time (int, optional): The hours to add up for. Defaults to 2.
        """

    @nextcord.slash_command(
        name="remove", description="Remove yourself from the add up list."
    )
    async def manual_remove(self, interaction: nextcord.Interaction):
        """Manually remove yourself from a pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """

    @nextcord.slash_command(name="status", description="Check the status of the pug.")
    async def waiting_status(self, interaction: nextcord.Interaction):
        """Check the status of the pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """

    @nextcord.slash_command(
        name="missing", description="Check who is missing from the pug."
    )
    async def missing_status(self, interaction: nextcord.Interaction):
        """Check who is missing from the pug.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
