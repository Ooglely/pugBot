"""Cog to hold commands to set up the registration part of the bot per server."""
import nextcord
from nextcord.ext import commands

from constants import TESTING_GUILDS, BOT_COLOR
from registration import (
    RegistrationIntroduction,
    RegistrationSettings,
    RegistrationRoles,
    GamemodeSelect,
    ModeSelect,
    BanSelect,
    ChannelSelect,
)
from util import is_runner, is_setup


class RegistrationSetupCog(commands.Cog):
    """Cog storing all the commands revolving around stats"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @is_setup()
    @is_runner()
    @nextcord.slash_command(
        name="registration",
        description="Setup tf.oog.pw registration for this server.",
        guild_ids=TESTING_GUILDS,
    )
    async def setup_registration(self, interaction: nextcord.Interaction):
        """Setup tf.oog.pw registration for this server."""
        settings = RegistrationSettings()
        settings.import_from_db(interaction.guild.id)
        setup_embed = nextcord.Embed(
            title="Registration Setup",
            color=BOT_COLOR,
            description="Registration allows for you to link new members of the server to https://tf.oog.pw/register, which can give them division roles based on their RGL experience.\n\nYou can have it go off either their current or highest division played, in either 6s or Highlander.\n\nYou will need to create your own division roles. You will match the divisions with the role you would like to be assigned in the setup menu.",
        )
        introduction = RegistrationIntroduction()
        await interaction.send(embed=setup_embed, view=introduction, ephemeral=True)
        await introduction.wait()
        action = introduction.action
        if action == "disable":
            settings.enabled = False
            settings.export_to_db(interaction.guild.id)
            setup_embed.description = "Registration has been disabled."
            await interaction.edit_original_message(embed=setup_embed, view=None)
            await interaction.delete_original_message(delay=5)
            return
        if action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        settings.enabled = True

        roles_view = RegistrationRoles(
            ["newcomer", "amateur", "intermediate"], settings.roles
        )
        setup_embed.description = "Please select the roles you would like to be assigned to each division. You can select one role for multiple divisions, but you must select at least one role for each division.\n\n**Note: Due to client-side discord limitations, you may need to SEARCH for the role in the select menu.**"
        await interaction.edit_original_message(embed=setup_embed, view=roles_view)
        await roles_view.wait()
        if roles_view.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        # Discord bugs client-side and doesn't update the view properly, so we need to clear the view and re-add it
        await interaction.edit_original_message(embed=setup_embed, view=None)

        # Discord doesn't allow 6 role selects at once, so I split it into two views
        roles_view_two = RegistrationRoles(
            ["main", "advanced", "invite"], roles_view.roles
        )
        await interaction.edit_original_message(embed=setup_embed, view=roles_view_two)
        await roles_view_two.wait()
        if roles_view_two.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        settings.roles = roles_view_two.roles

        # Gamemode select
        gamemode_view = GamemodeSelect()
        setup_embed.description = (
            "Please select the gamemode you would like to use for role assignment."
        )
        await interaction.edit_original_message(embed=setup_embed, view=gamemode_view)
        await gamemode_view.wait()
        settings.gamemode = gamemode_view.selection

        # Mode select
        mode_view = ModeSelect()
        setup_embed.description = "Please select the mode you would like to use for role assignment.\n\nYou can either go by the highest division played, or the current division played."
        await interaction.edit_original_message(embed=setup_embed, view=mode_view)
        await mode_view.wait()
        settings.mode = mode_view.selection

        # Ban select
        ban_view = BanSelect()
        setup_embed.description = "Would you like to automatically ban players that are RGL banned? If you select yes, you will have to select a ban role to be used."
        await interaction.edit_original_message(embed=setup_embed, view=ban_view)
        await ban_view.wait()
        settings.ban = ban_view.selection
        if ban_view.selection:
            ban_role_view = RegistrationRoles(["ban"], settings.roles)
            setup_embed.description = "Please select the role you would like to be assigned to banned players."
            await interaction.edit_original_message(
                embed=setup_embed, view=ban_role_view
            )
            await ban_role_view.wait()
            settings.roles = ban_role_view.roles

        # Channel select
        channel_view = ChannelSelect()
        setup_embed.description = "Lastly, please select the channels you would like to be used for new registrations and logging.\n\nJust like for selecting roles, you may need to search for it."
        await interaction.edit_original_message(embed=setup_embed, view=channel_view)
        await channel_view.wait()
        settings.channels["registration"] = channel_view.registration
        settings.channels["logs"] = channel_view.logs

        print(settings.__dict__)
        setup_embed.description = "Registration setup complete! Use /updateall to update all current members of the server, or wait for the bots daily update."
        settings.export_to_db(interaction.guild.id)
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=10)
