"""Commands for generating teams in pugs."""
import random
from typing import Optional, Dict

import nextcord
from nextcord.ext import commands

from constants import BOT_COLOR
from database import get_server, get_player_from_discord
from pug import CategorySelect, CategoryButton, TeamGenerationView, MoveView
from pug.setup import PugSetupCog
from registration import RegistrationSettings
from util import is_setup, is_runner


class PugRunningCog(commands.Cog):
    """Cog storing all the commands to run pugs"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @PugSetupCog.pug.subcommand(  # pylint: disable=no-member
        name="genteams", description="Generate teams for a pug."
    )
    @is_setup()
    @is_runner()
    async def genteams(
        self,
        interaction: nextcord.Interaction,
        team_size: Optional[int] = nextcord.SlashOption(
            name="team_size",
            description="The amount of players per team.",
            required=False,
        ),
    ):
        """Generate teams for a pug."""
        await interaction.response.defer()
        server = get_server(interaction.guild.id)
        if "pug_categories" not in server:
            await interaction.send(
                "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
            )
            return
        if len(server["pug_categories"]) == 0:
            await interaction.send(
                "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
            )
            return

        if team_size is None:
            team_size = 6

        select_view = CategorySelect()
        categories = server["pug_categories"]

        for category in categories:
            name: str = category["name"]
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
            if len(add_up_channel.members) < team_size * 2:
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

        pug_embed = nextcord.Embed(
            title="Generate Teams",
            color=BOT_COLOR,
            description="Select the category you would like to generate teams for.",
        )
        await interaction.send(embed=pug_embed, view=select_view)
        embed_status = await select_view.wait()
        if embed_status:
            return

        if select_view.name == "cancel":
            return

        for category in categories:
            if category["name"] == select_view.name:
                chosen_category = category

        add_up: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["add_up"]
        )
        red_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["red_team"]
        )
        blu_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["blu_team"]
        )
        next_pug: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["next_pug"]
        )

        pug_embed.description = None
        balancing_disabled = False

        reg_settings = RegistrationSettings()
        reg_settings.import_from_db(interaction.guild.id)
        if reg_settings.mode == "" or reg_settings.gamemode == "":
            pug_embed.description = "Teams are not able to be balanced as there are no registration settings set up.\nPlease run /registration setup to set up registration if you would like balanced teams."
            balancing_disabled = True

        gamemode: str
        if reg_settings.gamemode == "sixes":
            gamemode = "sixes"
        elif reg_settings.gamemode == "highlander":
            gamemode = "hl"

        teams = await self.generate_balanced_teams(
            await self.get_player_list(next_pug, add_up), team_size, reg_settings
        )

        while True:
            team_generation_view = TeamGenerationView(balancing_disabled)
            teams["red"].sort(
                key=lambda x: x
                if balancing_disabled
                else x["divison"][gamemode][reg_settings.mode],
                reverse=False,
            )
            red_team_string = ""
            red_level = 0
            red_count = 0
            for player in teams["red"]:
                if balancing_disabled:
                    divison = "?"
                else:
                    if player["divison"][gamemode][reg_settings.mode] == -1:
                        divison = "?"
                    else:
                        divison = player["divison"][gamemode][reg_settings.mode]
                        red_level += player["divison"][gamemode][reg_settings.mode]
                        red_count += 1
                red_team_string += f"[{divison}] <@{player['discord']}>\n"

            blu_team_string = ""
            blu_level = 0
            blu_count = 0
            for player in teams["blu"]:
                if balancing_disabled:
                    divison = "?"
                else:
                    if player["divison"][gamemode][reg_settings.mode] == -1:
                        divison = "?"
                    else:
                        divison = player["divison"][gamemode][reg_settings.mode]
                        blu_level += player["divison"][gamemode][reg_settings.mode]
                        blu_count += 1
                blu_team_string += f"[{divison}] <@{player['discord']}>\n"

            pug_embed.clear_fields()
            if red_count != 0 and blu_count != 0:
                pug_embed.add_field(
                    name=f"🔴 Red Team\nLevel: {(red_level/red_count):.2f}",
                    value=red_team_string,
                )
                pug_embed.add_field(
                    name=f"🔵 Blu Team\nLevel: {(blu_level/blu_count):.2f}",
                    value=blu_team_string,
                )
            else:
                pug_embed.add_field(name="🔴 Red Team", value=red_team_string)
                pug_embed.add_field(name="🔵 Blu Team", value=blu_team_string)

            await interaction.edit_original_message(
                embed=pug_embed, view=team_generation_view
            )
            status = await team_generation_view.wait()
            if status:
                break  # Handles time outs
            if team_generation_view.action == "move":
                pug_embed.description = "Moving players..."
                await interaction.edit_original_message(embed=pug_embed, view=None)
                for player in teams["red"]:
                    member = await interaction.guild.fetch_member(player["discord"])
                    await member.move_to(red_team)
                for player in teams["blu"]:
                    member = await interaction.guild.fetch_member(player["discord"])
                    await member.move_to(blu_team)
                pug_embed.description = "Done moving players!"
                await interaction.edit_original_message(embed=pug_embed, view=None)
                break

            if team_generation_view.action == "random":
                pug_embed.clear_fields()
                teams = await self.generate_random_teams(
                    await self.get_player_list(next_pug, add_up), team_size
                )

            if team_generation_view.action == "balanced":
                pug_embed.clear_fields()
                teams = await self.generate_balanced_teams(
                    await self.get_player_list(next_pug, add_up),
                    team_size,
                    reg_settings,
                )

    async def get_player_list(
        self, next_pug: nextcord.VoiceChannel, add_up: nextcord.VoiceChannel
    ):
        """Return a list of players in a voice channel.

        Args:
            channel (nextcord.VoiceChannel): The voice channel to get players from.

        Returns:
            list: A list of players in the voice channel.
        """
        players: Dict[str, list[Dict]] = {"next_pug": [], "add_up": []}
        for member in next_pug.members:
            try:
                player_data = get_player_from_discord(member.id)
            except LookupError:
                player_data = {
                    "discord": member.id,
                    "divison": {
                        "sixes": {"highest": -1, "current": -1},
                        "hl": {"highest": -1, "current": -1},
                    },
                }
            players["next_pug"].append(player_data)
        for member in add_up.members:
            try:
                player_data = get_player_from_discord(member.id)
            except LookupError:
                player_data = {
                    "discord": member.id,
                    "divison": {
                        "sixes": {"highest": -1, "current": -1},
                        "hl": {"highest": -1, "current": -1},
                    },
                }
            players["add_up"].append(player_data)
        return players

    async def generate_random_teams(self, players: dict, team_size):
        """Generate random teams for a pug.

        Args:
            players (list): A list of all players in the VC
            team_size (int): The amount of players per team.
            reg_settings (RegistrationSettings): The registration settings for the server.

        Returns:
            teams: The generated teams.
        """
        random.shuffle(players["next_pug"])
        random.shuffle(players["add_up"])
        players = players["next_pug"] + players["add_up"]

        red_team: list[dict] = []
        blu_team: list[dict] = []

        while len(red_team) < team_size and len(blu_team) < team_size:
            red_team.append(players.pop(0))
            blu_team.append(players.pop(0))

        teams = {"red": red_team, "blu": blu_team}
        return teams

    async def generate_balanced_teams(
        self, players: dict, team_size, reg_settings: RegistrationSettings
    ):
        """Generate balanced teams for a pug.

        Args:
            players (list): A list of all players in the VC
            team_size (int): The amount of players per team.
            reg_settings (RegistrationSettings): The registration settings for the server.

        Returns:
            teams: The generated teams.
        """
        if reg_settings.mode == "" or reg_settings.gamemode == "":
            teams = await self.generate_random_teams(players, team_size)
            return teams

        gamemode: str
        if reg_settings.gamemode == "sixes":
            gamemode = "sixes"
        elif reg_settings.gamemode == "highlander":
            gamemode = "hl"

        random.shuffle(players["next_pug"])
        random.shuffle(players["add_up"])
        players["next_pug"].sort(
            key=lambda x: 10
            if x["divison"][gamemode][reg_settings.mode] == -1
            else x["divison"][gamemode][reg_settings.mode],
            reverse=False,
        )
        players["add_up"].sort(
            key=lambda x: 10
            if x["divison"][gamemode][reg_settings.mode] == -1
            else x["divison"][gamemode][reg_settings.mode],
            reverse=False,
        )
        players = players["next_pug"] + players["add_up"]

        red_team: list[dict] = []
        blu_team: list[dict] = []
        count = 0

        while len(red_team) < team_size and len(blu_team) < team_size:
            if count % 2 == 0:
                red_team.append(players.pop(0))
                blu_team.append(players.pop(0))
            else:
                blu_team.append(players.pop(0))
                red_team.append(players.pop(0))
            count += 1

        teams = {"red": red_team, "blu": blu_team}
        return teams

    @PugSetupCog.pug.subcommand(  # pylint: disable=no-member
        name="move", description="Moves players after a pug is done."
    )
    @is_setup()
    @is_runner()
    async def move(self, interaction: nextcord.Interaction):
        """Move players back after a pug is done."""
        await interaction.response.defer()
        server = get_server(interaction.guild.id)
        if "pug_categories" not in server:
            await interaction.send(
                "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
            )
            return
        if len(server["pug_categories"]) == 0:
            await interaction.send(
                "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
            )
            return

        select_view = CategorySelect()
        categories = server["pug_categories"]

        for category in categories:
            name: str = category["name"]
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
            if (
                len(red_team_channel.members) == 0
                and len(blu_team_channel.members) == 0
            ):
                disabled = True
                name += " (No players to move)"
            if interaction.user.voice is not None:
                if interaction.user.voice.channel == (
                    red_team_channel,
                    blu_team_channel,
                    add_up_channel,
                ):
                    color = nextcord.ButtonStyle.green

            button = CategoryButton(name=name, color=color, disabled=disabled)
            select_view.add_item(button)

        pug_embed = nextcord.Embed(
            title="Generate Teams",
            color=BOT_COLOR,
            description="Select the category to move users in.",
        )
        await interaction.send(embed=pug_embed, view=select_view)
        status = await select_view.wait()
        if status:
            return

        if select_view.name == "cancel":
            return

        for category in categories:
            if category["name"] == select_view.name:
                chosen_category = category

        add_up: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["add_up"]
        )
        red_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["red_team"]
        )
        blu_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["blu_team"]
        )
        next_pug: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category["next_pug"]
        )

        red_players = []
        blu_players = []
        waiting_players = []
        moving_string = f"Moving players from <#{add_up.id}> to <#{next_pug.id}>..."
        pug_embed.title = "Moving players..."
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=None)
        for member in add_up.members:
            waiting_players.append(member)
            await member.move_to(next_pug)
        moving_string += (
            f"\nDone!\n\nMoving players from <#{red_team.id}> to <#{add_up.id}>..."
        )
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=None)
        for member in red_team.members:
            red_players.append(member)
            await member.move_to(add_up)
        moving_string += (
            f"\nDone!\n\nMoving players from <#{blu_team.id}> to <#{add_up.id}>..."
        )
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=None)
        for member in blu_team.members:
            blu_players.append(member)
            await member.move_to(add_up)
        moving_string += "\nDone!"

        move_view = MoveView()
        pug_embed.title = "Players moved!"
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=move_view)
        await move_view.wait()

        if move_view.action == "cancel":
            return
        if move_view.action == "move":
            moving_string = f"Moving players from <#{next_pug.id}> to <#{add_up.id}>..."
            pug_embed.title = "Moving players back..."
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in waiting_players:
                await member.move_to(add_up)
            moving_string += (
                f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{red_team.id}>..."
            )
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in red_players:
                await member.move_to(red_team)
            moving_string += (
                f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{blu_team.id}>..."
            )
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in blu_players:
                await member.move_to(blu_team)
            moving_string += "\nDone!"

            pug_embed.title = "Done moving players back."
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)

            await interaction.delete_original_message(delay=10)
            return

        await interaction.delete_original_message(delay=10)