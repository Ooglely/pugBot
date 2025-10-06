"""This cog contains the logs command and its subcommands."""

import nextcord
from nextcord.ext import commands, application_checks
from nextcord.enums import ChannelType

from database import BotCollection
from pug.pug import PugRunningCog
from menus import BotMenu
from menus.templates import send_boolean_menu, send_channel_prompt
from constants import BOT_COLOR

guild_configs = BotCollection("guilds", "config")


class LogsCog(commands.Cog):
    """This cog contains the logs command and its subcommands."""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

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
        if interaction.guild is None or not isinstance(
            interaction.guild, nextcord.Guild
        ):
            return
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

        menu: BotMenu = BotMenu(interaction.user.id, setup_embed)
        if menu.embed is None:
            return

        menu.embed.description = "Would you like to enable logs?"
        try:
            result: bool = await send_boolean_menu(menu, interaction)
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return
        if not result:
            log_settings["enabled"] = False
            await guild_configs.update_item(
                {"guild": interaction.guild.id}, {"$set": {"logs": log_settings}}
            )
            setup_embed.description = "Logs have been disabled."
            await interaction.edit_original_message(embed=setup_embed, view=None)
            await interaction.delete_original_message(delay=30)
            return
        log_settings["enabled"] = True

        menu.embed.description = (
            "Please select the channel you want logs to be sent to."
        )
        try:
            channel: list[nextcord.TextChannel] = await send_channel_prompt(
                menu, interaction, ["Logs Channel"], True, [ChannelType.text]
            )
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return
        except ValueError:
            await interaction.edit_original_message(
                content="No channel selected. Please try again."
            )
            await interaction.delete_original_message(delay=10)
            return
        log_settings["channel"] = channel[0].id

        menu.embed.description = "Would you like to embed a picture of logs?\nThis is done through using loogs.tf. More info can be found at https://loogs.tf/"
        try:
            result = await send_boolean_menu(menu, interaction)
        except TimeoutError:
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        log_settings["loogs"] = menu.action == "enable"

        menu.embed.description = f"Logs have been setup.\nEnabled: {log_settings['enabled']}\nChannel: <#{log_settings['channel']}>\nLoogs.tf Enabled: {log_settings['loogs']}"
        await interaction.edit_original_message(embed=menu.embed, view=None)
        await interaction.delete_original_message(delay=60)
        await guild_configs.update_item(
            {"guild": interaction.guild.id}, {"$set": {"logs": log_settings}}
        )
