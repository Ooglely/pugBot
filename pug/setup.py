"""Cog to set up pug categories for the server."""
import nextcord
from nextcord.ext import commands

from constants import BOT_COLOR
from database import BotCollection
from pug import (
    PugChannelSelect,
    FirstToChannelSelect,
    FirstToSelect,
    PugCategory,
    CategorySelect,
    CategoryButton,
)
from util import is_setup, is_runner

category_db = BotCollection("guilds", "categories")


class PugSetupCog(commands.Cog):
    """Cog storing all the commands to setup pugs"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @nextcord.slash_command()
    async def pug(self, interaction: nextcord.Interaction):
        """
        This is the main slash command that will be the prefix of all commands below.
        This will never get called since it has subcommands.
        """

    @pug.subcommand()
    async def category(self, interaction: nextcord.Interaction):
        """Never gets called, just a placeholder for the subcommand."""

    @category.subcommand(name="add", description="Add a pug category to the server.")
    @is_setup()
    @is_runner()
    async def pug_category_add(
        self,
        interaction: nextcord.Interaction,
        name: str = nextcord.SlashOption(
            name="name", description="The name for the category.", required=True
        ),
    ):
        """Add a pug category to the server.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        setup_embed = nextcord.Embed(
            title="Pug Category Setup",
            color=BOT_COLOR,
            description="Adding a pug category allows you to setup team generation and move commands.\n\nPlease select the add up/selecting channel, and the RED and BLU team channels.\nYou may need to search for them.",
        )
        pug_category = PugCategory(name)

        # Add a pug category to the server
        channel_select_view = PugChannelSelect()
        await interaction.send(embed=setup_embed, view=channel_select_view)
        await channel_select_view.wait()
        if channel_select_view.action == "cancel":
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        pug_category.add_up = channel_select_view.add_up
        pug_category.red_team = channel_select_view.red_team
        pug_category.blu_team = channel_select_view.blu_team
        # First to x select
        first_to = {
            "enabled": False,
            "num": 0,
        }

        first_to_channel = FirstToChannelSelect()
        setup_embed.description = "Please select the In Next Pug channel. This is the channel that the waiting players will be moved to, and the first x players if it is enabled."
        await interaction.edit_original_message(
            embed=setup_embed, view=first_to_channel
        )
        await first_to_channel.wait()
        pug_category.next_pug = first_to_channel.first_to

        first_to_view = FirstToSelect()
        setup_embed.description = "If you would like to use the first to x system, please select the number of players required to add up.\nThis will move the first x players to the chosen In Next Pug channel.\n\n**Not Implemented Yet**"
        await interaction.edit_original_message(embed=setup_embed, view=first_to_view)
        await first_to_view.wait()
        first_to["enabled"] = first_to_view.selection
        first_to["num"] = first_to_view.num

        pug_category.first_to = first_to

        # Add the category to the database
        await pug_category.add_to_db(interaction.guild.id)

        setup_embed.description = "Pug category setup complete! You can now use team generation and move commands in these channels."
        setup_embed.add_field(
            name="Channels",
            value=f"Add Up: <#{pug_category.add_up}>\nRED: <#{pug_category.red_team}>\nRED: <#{pug_category.blu_team}>",
        )
        setup_embed.add_field(
            name="First To",
            value=f"Enabled: {pug_category.first_to['enabled']}\nMode: {pug_category.first_to['num']}\nChannel: <#{pug_category.next_pug}>",
        )

        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=20)

    @category.subcommand(
        name="remove", description="Remove a pug category from the server."
    )
    @is_setup()
    @is_runner()
    async def pug_category_remove(self, interaction: nextcord.Interaction):
        """Remove a pug category from the server.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        await interaction.response.defer()

        # Get a list of pug categories
        try:
            result = await category_db.find_item({"_id": interaction.guild.id})
        except LookupError:
            await interaction.send("There are no pug categories to remove.")
            return

        categories = result["categories"]

        if len(categories) == 0:
            await interaction.send("There are no pug categories to remove.")
            return

        setup_embed = nextcord.Embed(
            title="Remove Pug Category",
            color=BOT_COLOR,
            description="Select a pug category to remove.",
        )

        select_view = CategorySelect()

        for category in categories.keys():
            print(category)
            button = CategoryButton(name=category)
            select_view.add_item(button)

        await interaction.send(embed=setup_embed, view=select_view)
        await select_view.wait()
        category_to_remove: str = select_view.name

        if category_to_remove == "cancel":
            return

        category = PugCategory(category_to_remove)
        await category.remove_from_db(interaction.guild.id)

        setup_embed.description = f"Removed pug category {category_to_remove}."
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=20)
