"""Commands for randomly rolling medics in pugs."""
import datetime
import random
from typing import Optional, Set

import nextcord
from nextcord.ext import commands, tasks

from constants import BOT_COLOR
from database import (
    BotCollection,
    get_server,
    add_med_immune_player,
    remove_med_immune_player,
    clear_med_immunity_by_guild, clear_med_immunity_all_guilds,
)
from pug import (
    CategorySelect,
    CategoryButton,
    Player,
    PugCategory,
    BooleanView,
)
from pug.pug import PugRunningCog, get_player_dict
from util import is_setup, is_runner

category_db = BotCollection("guilds", "categories")

reset_time = datetime.time(hour=13, minute=0, tzinfo=datetime.timezone.utc)


class PugMedicCog(commands.Cog):
    """Cog storing all the commands for medic immunity"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot
        self.__clear_all.start() # pylint: disable=no-member

    @PugRunningCog.pug.subcommand() # pylint: disable=no-member
    async def medic(self, interaction: nextcord.Interaction):
        """Never gets called, just a placeholder for the subcommand."""

    @tasks.loop(time=reset_time)
    async def __clear_all(self):
        clear_med_immunity_all_guilds()

    @medic.subcommand(  # pylint: disable=no-member
        name="roll",
        description="Randomly selects a non-immune player to play medic.",
    )
    @is_setup()
    @is_runner()
    async def roll_medic(
        self,
        interaction: nextcord.Interaction,
        team_size: Optional[int] = nextcord.SlashOption(
            name="team_size",
            description="The size of the teams, default 6",
            required=False,
            default=6,
        ),
    ):
        await interaction.response.defer()

        # Get a list of pug categories
        try:
            result = await category_db.find_item({"_id": interaction.guild.id})
            categories = result["categories"]
            if len(categories) == 0:
                raise LookupError
        except LookupError:
            await interaction.send(
                "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
            )
            return

        select_view = CategorySelect()

        for name, category in categories.items():
            disabled: bool = False
            color = nextcord.ButtonStyle.gray
            add_up_channel: nextcord.VoiceChannel = interaction.guild.get_channel(
                category["add_up"]
            )
            red_team_channel: nextcord.VoiceChannel = interaction.guild.get_channel(
                category["red_team"]
            )
            blu_team_channel: nextcord.VoiceChannel = interaction.guild.get_channel(
                category["blu_team"]
            )
            next_pug_channel: nextcord.VoiceChannel = interaction.guild.get_channel(
                category["next_pug"]
            )
            if (
                len(add_up_channel.members) + len(next_pug_channel.members)
            ) < team_size * 2:
                disabled = True
                name += " (Not enough players)"
            if len(red_team_channel.members) > 0 or len(blu_team_channel.members) > 0:
                disabled = True
                name += " (Pug in progress)"
            if (
                interaction.user.voice is not None
                and interaction.user.voice.channel
                == (next_pug_channel or add_up_channel)
            ):
                color = nextcord.ButtonStyle.green

            button = CategoryButton(name=name, color=color, disabled=disabled)
            select_view.add_item(button)

        med_embed = nextcord.Embed(
            title="Roll Medic",
            color=BOT_COLOR,
            description="Select the category you would like to roll medic for.",
        )
        await interaction.send(embed=med_embed, view=select_view)
        embed_status = await select_view.wait()
        if embed_status or select_view.name == "cancel":
            return

        chosen_category: PugCategory = PugCategory(
            select_view.name, categories[select_view.name]
        )

        add_up: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.add_up
        )
        next_pug: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.next_pug
        )

        server = get_server(interaction.guild.id)
        immune_players: Set[int] = set(server["immune"])

        players = await get_player_dict(next_pug, add_up)

        immune_chosen = False  # True in the very rare case that all players in next pug/add up are already immune
        medic: Player | None = None
        # All players in the next pug must be picked from this channel including med
        if len(players["next_pug"]) >= team_size * 2:
            random.shuffle(players["next_pug"])
            for player in players["next_pug"]:
                if player.discord not in immune_players:
                    medic = player
                    break
            if not medic:
                medic = players["next_pug"][0]
                immune_chosen = True
        else:
            random.shuffle(players["add_up"])
            for player in players["add_up"]:
                if player.discord not in immune_players:
                    medic = player
                    break
            if not medic:
                medic = players["add_up"][0]
                immune_chosen = True

        med_embed.description = f"Rolled <@{medic.discord}> as medic."

        if not immune_chosen:
            med_embed.description += "\n\nGive player medic roll immunity?"

            boolean_view = BooleanView()

            await interaction.edit_original_message(embed=med_embed, view=boolean_view)
            status = await boolean_view.wait()

            med_embed.clear_fields()
            if status or not boolean_view.action:
                med_embed.description = f"<@{medic.discord}> not given med roll immunity."
            else:
                med_embed.description = f"<@{medic.discord}> given med roll immunity."
                add_med_immune_player(interaction.guild.id, medic.discord)
        else:
            med_embed.description += "\nAll players are already immune so an already immune player was chosen."

        await interaction.edit_original_message(embed=med_embed, view=None)

    @medic.subcommand(  # pylint: disable=no-member
        name="immune", description="Manually set a player as immune to medic roll."
    )
    @is_setup()
    @is_runner()
    async def set_med_immune(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name="discord", description="The Discord user to make immune", required=True
        ),
    ):
        await interaction.response.defer()
        add_med_immune_player(interaction.guild.id, user.id)

        med_embed = nextcord.Embed(
            title="Set User Immune to Medic Roll",
            color=BOT_COLOR,
            description=f"<@{user.id}> is now immune to medic roll.",
        )
        await interaction.send(embed=med_embed)

    @medic.subcommand(  # pylint: disable=no-member
        name="remove",
        description="Manually remove a player from being immune to medic roll.",
    )
    @is_setup()
    @is_runner()
    async def remove_med_immune(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name="discord",
            description="The Discord user to remove immunity from",
            required=True,
        ),
    ):
        await interaction.response.defer()
        remove_med_immune_player(interaction.guild.id, user.id)

        med_embed = nextcord.Embed(
            title="Removed User Immune to Medic Roll",
            color=BOT_COLOR,
            description=f"<@{user.id}> is no longer immune to medic roll.",
        )
        await interaction.send(embed=med_embed)

    @medic.subcommand(  # pylint: disable=no-member
        name="remove_all",
        description="Manually set a player as immune to medic roll.",
    )
    @is_setup()
    @is_runner()
    async def remove_all_med_immune(self, interaction: nextcord.Interaction):
        await interaction.response.defer()
        clear_med_immunity_by_guild(interaction.guild.id)

        med_embed = nextcord.Embed(
            title="Remove Immunity From All Players",
            color=BOT_COLOR,
            description="Are you certain you want to clear medic roll immunity from all players?",
        )
        boolean_view = BooleanView()
        await interaction.send(embed=med_embed, view=boolean_view)
        view_status = await boolean_view.wait()

        if view_status or not boolean_view.action:
            med_embed.description = "Did not remove medic roll immunity."
        else:
            med_embed.description = "Removed medic roll immunity from all players."

        await interaction.edit_original_message(embed=med_embed, view=None)

    @medic.subcommand(  # pylint: disable=no-member
        name="view",
        description="View all currently medic roll immune players.",
    )
    @is_setup()
    @is_runner()
    async def view_all_med_immune(self, interaction: nextcord.Interaction):
        await interaction.response.defer()
        server = get_server(interaction.guild.id)

        immune_embed = nextcord.Embed(
            title="Immune Players",
            color=BOT_COLOR,
        )

        if "immune" not in server or len(server["immune"]) == 0:
            immune_embed.description = "No players are currently immune to medic roll!"
        else:
            immune = server["immune"]
            description: str = ""

            for i, discord_id in enumerate(immune):
                description += f"<@{discord_id}>"
                if i < len(immune):
                    description += "\n"

            immune_embed.description = description

        await interaction.send(embed=immune_embed)
