"""Cog to set up pug categories for the server."""

import nextcord
from nextcord.ext import commands
from nextcord.abc import GuildChannel
from nextcord.enums import ChannelType

from constants import BOT_COLOR
from database import BotCollection
from menus import BotMenu
from menus.templates import send_channel_prompt
from pug import (
    PugCategory,
    CategorySelect,
    CategoryButton,
)
from pug.pug import PugRunningCog
from util import is_runner, guild_config_check

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

    @guild_config_check()
    @is_runner()
    @category.subcommand(name="add", description="Add a pug category to the server.")
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
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

        setup_embed = nextcord.Embed(
            title="Pug Category Setup",
            color=BOT_COLOR,
            description="Adding a pug category allows you to setup team generation and move commands.\n\nPlease select the add up/selecting channel, the RED and BLU team channels, and the 'In Next Pug' channel, which is the channel waiting players get moved to.\nYou may need to search for them.",
        )
        menu: BotMenu = BotMenu(embed=setup_embed, user_id=interaction.user.id)
        pug_category = PugCategory(name)

        # Add a pug category to the server
        try:
            channels: list[GuildChannel] = await send_channel_prompt(
                menu,
                interaction,
                ["Add Up/Selecting", "RED Team", "BLU Team", "In Next Pug/Waiting"],
                True,
                [ChannelType.voice],
            )
        except ValueError:
            await interaction.send("You must select a channel for each entry.")
            return
        except TimeoutError:
            await interaction.edit_original_message(view=None)
            await interaction.delete_original_message(delay=1)
            return
        pug_category.add_up = channels[0].id
        pug_category.red_team = channels[1].id
        pug_category.blu_team = channels[2].id
        pug_category.next_pug = channels[3].id

        # Add the category to the database
        await pug_category.add_to_db(interaction.guild.id)

        setup_embed.description = "Pug category setup complete! You can now use team generation and move commands in these channels."
        setup_embed.add_field(
            name="Channels",
            value=f"Add Up: <#{pug_category.add_up}>\nRED: <#{pug_category.red_team}>\nBLU: <#{pug_category.blu_team}>\nIn Next Pug: <#{pug_category.next_pug}>",
        )

        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=20)

    @guild_config_check()
    @is_runner()
    @category.subcommand(
        name="remove", description="Remove a pug category from the server."
    )
    async def pug_category_remove(self, interaction: nextcord.Interaction):
        """Remove a pug category from the server.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        await interaction.response.defer()

        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

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

    @guild_config_check()
    @is_runner()
    @roles.subcommand(
        name="add", description="Add a role to the role balancing system."
    )
    async def role_add(
        self,
        interaction: nextcord.Interaction,
        role: nextcord.Role = nextcord.SlashOption(
            name="role", description="The role to add.", required=True
        ),
        value: int = nextcord.SlashOption(
            name="value", description="The point value to give the role.", required=True
        ),
        emote: str | None = nextcord.SlashOption(
            name="emote", description="The emote to use for the role.", required=False
        ),
    ):
        """Add a role to the role balancing system.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
            role (nextcord.Role): The role to add to the system.
            value (int): The point value to give the role.
            emote (str | None): The emote to use for the role.
        """
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

        guild_config = await config_db.find_item({"guild": interaction.guild.id})
        if "roles" not in guild_config:
            guild_roles = {}
        else:
            guild_roles = guild_config["roles"]

        if emote is not None:
            if emote.startswith("<") and emote.endswith(">"):
                emote_obj = emote
            else:
                emote_obj = nextcord.utils.get(interaction.guild.emojis, name=emote)
            if emote_obj is None:
                await interaction.send("The emote you provided is not in this server.")
                return
        emote_string = emote if emote is None else str(emote_obj)

        guild_roles[str(role.id)] = {
            "value": value,
            "icon": emote_string,
        }

        await self.update_role_settings(interaction.guild.id, guild_roles)
        await interaction.send(
            f"Added role {role.name} to the role balancing system with a value of {value}."
        )

    @guild_config_check()
    @is_runner()
    @roles.subcommand(
        name="remove", description="Remove a role from the role balancing system."
    )
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
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.manage_guild:
            await interaction.send(
                "You need Manage Guild permissions to run this command."
            )
            return

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

    @guild_config_check()
    @is_runner()
    @roles.subcommand(
        name="list", description="List the roles in the role balancing system."
    )
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
            if value["icon"] is None:
                role_list += f"<@&{role_id}>: {value['value']}\n"
            else:
                role_list += f"{value['icon']} <@&{role_id}>: {value['value']}\n"
        roles_embed.add_field(name="Roles", value=role_list)

        await interaction.send(embed=roles_embed)

    async def update_role_settings(self, guild: int, settings: dict):
        """Update the guild settings in the database.

        Args:
            guild (int): The guild ID to update.
            settings (dict): The settings to update.
        """
        await config_db.update_item({"guild": guild}, {"$set": {"roles": settings}})
