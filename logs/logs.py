"""This cog contains the logs command and its subcommands."""
import nextcord
from nextcord.ext import commands, application_checks
from database import BotCollection
from pug.pug import PugRunningCog
from registration import TrueFalseSelect
from constants import BOT_COLOR

guild_configs = BotCollection("guilds", "config")


class LogsChannelSelect(nextcord.ui.View):
    """View to select the channel to send logs to."""

    def __init__(self):
        super().__init__()
        self.action = None
        self.logs = None

    @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green)
    async def finish(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Continues setup"""
        self.action = "continue"
        await _interaction.response.edit_message(view=None)
        self.stop()

    @nextcord.ui.button(label="Cancel", style=nextcord.ButtonStyle.red)
    async def cancel(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Cancels setup"""
        self.action = "cancel"
        await _interaction.response.edit_message(view=None)
        self.stop()

    @nextcord.ui.channel_select(placeholder="Logs Channel")
    async def logs_channel(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select the channel that logs will be sent in.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.logs = channel.values[0].id


class LogsCog(commands.Cog):
    """This cog contains the logs command and its subcommands."""

    def __init__(self, bot):
        self.bot = bot

    @PugRunningCog.pug.subcommand()  ## pylint: disable=no-member
    async def logs(self, interaction: nextcord.Interaction):
        """
        This is a subcommand group of the '/pug' slash command.
        All subcommands of this group will be prefixed with '/pug logs'.
        This will never get called since it has subcommands.
        """

    @application_checks.has_permissions(manage_guild=True)
    @logs.subcommand(
        name="setup", description="Set up the logs channel for this server."
    )
    async def logs_setup(self, interaction: nextcord.Interaction):
        """Setup the logs channel."""
        setup_embed = nextcord.Embed(
            title="Logs Setup",
            color=BOT_COLOR,
        )
        try:
            guild_settings = await guild_configs.find_item(
                {"guild": interaction.guild.id}
            )
        except LookupError:
            await interaction.send(
                "This server has not been setup yet. Please run /setup first."
            )
            return

        if "logs" in guild_settings:
            log_settings = guild_settings["logs"]
        else:
            log_settings = {
                "enabled": False,
                "channel": None,
                "loogs": False,
            }

        setup_embed.description = "Would you like to enable logs?"
        logs_enable = TrueFalseSelect()
        await interaction.send(embed=setup_embed, view=logs_enable)
        setup_status = await logs_enable.wait()
        if setup_status:
            await interaction.delete_original_message(delay=1)
            return
        if not logs_enable.selection:
            log_settings["enabled"] = False
            await guild_configs.update_item(
                {"guild": interaction.guild.id}, {"$set": {"logs": log_settings}}
            )
            setup_embed.description = "Logs have been disabled."
            await interaction.edit_original_message(embed=setup_embed, view=None)
            await interaction.delete_original_message(delay=30)
            return
        await interaction.edit_original_message(view=None)
        log_settings["enabled"] = True

        setup_embed.description = (
            "Please select the channel you want logs to be sent to."
        )
        channel_setup = LogsChannelSelect()
        await interaction.edit_original_message(embed=setup_embed, view=channel_setup)
        setup_status = await channel_setup.wait()
        if setup_status or channel_setup.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        log_settings["channel"] = channel_setup.logs
        await interaction.edit_original_message(view=None)

        setup_embed.description = "Would you like to embed a picture of logs?\nThis is done through using loogs.tf. More info can be found at https://loogs.tf/\nThis website is in development, and may be unstable."
        loogs_select = TrueFalseSelect()
        await interaction.edit_original_message(embed=setup_embed, view=loogs_select)
        setup_status = await loogs_select.wait()
        if setup_status:
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        log_settings["loogs"] = loogs_select.selection

        setup_embed.description = f"Logs have been setup.\nEnabled: {log_settings['enabled']}\nChannel: <#{log_settings['channel']}>\nLoogs.tf Enabled: {log_settings['loogs']}"
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=60)
        await guild_configs.update_item(
            {"guild": interaction.guild.id}, {"$set": {"logs": log_settings}}
        )
