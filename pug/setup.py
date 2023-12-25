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
from pug.pug import PugRunningCog
from util import is_setup, is_runner, guild_config_check

category_db = BotCollection("guilds", "categories")
config_db = BotCollection("guilds", "config")


class PugSetupCog(commands.Cog):
    """Cog storing all the commands to setup pugs"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @PugRunningCog.pug.subcommand()  # pylint: disable=no-member
    async def category(self, interaction: nextcord.Interaction):
        """Never gets called, just a placeholder for the subcommand."""

    @nextcord.slash_command()
    async def roles(self, interaction: nextcord.Interaction):
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

    @roles.subcommand(
        name="add", description="Add a role to the role balancing system."
    )
    @guild_config_check()
    @is_runner()
    async def role_add(
        self,
        interaction: nextcord.Interaction,
        role: nextcord.Role = nextcord.SlashOption(
            name="role", description="The role to add.", required=True
        ),
        value: int = nextcord.SlashOption(
            name="value", description="The point value to give the role.", required=True
        ),
    ):
        """Add a role to the role balancing system.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            role (nextcord.Role): The role to add to the system.
            value (int): The point value to give the role.
        """
        guild_config = await config_db.find_item({"guild": interaction.guild.id})
        if "roles" not in guild_config:
            guild_roles = {}
        else:
            guild_roles = guild_config["roles"]

        guild_roles[str(role.id)] = value
        await self.update_role_settings(interaction.guild.id, guild_roles)
        await interaction.send(
            f"Added role {role.name} to the role balancing system with a value of {value}."
        )

    @roles.subcommand(
        name="remove", description="Remove a role from the role balancing system."
    )
    @guild_config_check()
    @is_runner()
    async def role_remove(
        self,
        interaction: nextcord.Interaction,
        role: nextcord.Role = nextcord.SlashOption(
            name="role", description="The role to add.", required=True
        ),
    ):
        """Remove a role from the role balancing system.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            role (nextcord.Role): The role to remove from the system.
        """
        guild_config = await config_db.find_item({"guild": interaction.guild.id})
        if "roles" not in guild_config:
            guild_roles = {}
        else:
            guild_roles = guild_config["roles"]

        if str(role.id) not in guild_roles:
            await interaction.send(
                f"Role {role.name} is not in the role balancing system."
            )
            return

        del guild_roles[str(role.id)]
        await self.update_role_settings(interaction.guild.id, guild_roles)
        await interaction.send(
            f"Removed role {role.name} from the role balancing system."
        )

    @roles.subcommand(
        name="list", description="List the roles in the role balancing system."
    )
    @guild_config_check()
    @is_runner()
    async def role_list(
        self,
        interaction: nextcord.Interaction,
    ):
        """List the roles in the role balancing system.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        guild_config = await config_db.find_item({"guild": interaction.guild.id})
        if "roles" not in guild_config:
            guild_roles = {}
        else:
            guild_roles = guild_config["roles"]

        if len(guild_roles) == 0:
            await interaction.send("There are no roles in the role balancing system.")
            return

        roles_embed = nextcord.Embed(title="Role Balancing System", color=BOT_COLOR)

        role_list = ""
        for role_id, value in guild_roles.items():
            role_list += f"<@&{role_id}>: {value}\n"
        roles_embed.add_field(name="Roles", value=role_list)

        await interaction.send(embed=roles_embed)

    async def update_role_settings(self, guild: int, settings: dict):
        """Update the guild settings in the database.

        Args:
            guild (int): The guild ID to update.
            settings (dict): The settings to update.
        """
        await config_db.update_item({"guild": guild}, {"$set": {"roles": settings}})
