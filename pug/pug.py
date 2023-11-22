"""Commands for generating teams in pugs."""
import random
from typing import Optional, Dict, List

import nextcord
from nextcord.ext import commands

from constants import BOT_COLOR
from database import BotCollection
from logs import Player
from logs.searcher import LogSearcher
from logs.elo import get_elo
from pug import (
    CategorySelect,
    CategoryButton,
    TeamGenerationView,
    MoveView,
    PugPlayer,
    PugCategory,
)

from registration import RegistrationSettings
from util import is_setup, is_runner

category_db = BotCollection("guilds", "categories")


async def get_player_dict(
    next_pug: nextcord.VoiceChannel, add_up: nextcord.VoiceChannel
) -> Dict[str, List[PugPlayer]]:
    """Return a dict of players in two voice channels.

    Args:
        next_pug (nextcord.VoiceChannel): A voice channel to get players from.
        add_up (nextcord.VoiceChannel): A voice channel to get players from.

    Returns:
        dict: A dict of players in the voice channels.
    """
    players: Dict[str, list[PugPlayer]] = {"next_pug": [], "add_up": []}
    for member in next_pug.members:
        player = PugPlayer(discord=member.id)
        players["next_pug"].append(player)
    for member in add_up.members:
        player = PugPlayer(discord=member.id)
        players["add_up"].append(player)
    return players


async def generate_random_teams(
    players: Dict[str, List[PugPlayer]], team_size: int
) -> Dict[str, list[PugPlayer]]:
    """Generate random teams for a pug.

    Args:
        players (list): A list of all players in the VC
        team_size (int): The amount of players per team.

    Returns:
        teams: The generated teams.
    """
    random.shuffle(players["next_pug"])
    random.shuffle(players["add_up"])
    all_players: List[PugPlayer] = players["next_pug"] + players["add_up"]

    red_team: list[PugPlayer] = []
    blu_team: list[PugPlayer] = []

    while len(red_team) < team_size and len(blu_team) < team_size:
        red_team.append(all_players.pop(0))
        blu_team.append(all_players.pop(0))

    teams = {"red": red_team, "blu": blu_team}
    return teams


async def generate_balanced_teams(
    players: Dict[str, List[PugPlayer]],
    team_size,
    reg_settings: RegistrationSettings,
) -> Dict[str, List[PugPlayer]]:
    """Generate balanced teams for a pug.

    Args:
        players (dict): A dictionary of all players in the VCs
        team_size (int): The amount of players per team.
        reg_settings (RegistrationSettings): The registration settings for the server.

    Returns:
        teams: The generated teams.
    """
    if reg_settings.mode == "" or reg_settings.gamemode == "":
        teams = await generate_random_teams(players, team_size)
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
        if x.division[gamemode][reg_settings.mode] == -1
        else x.division[gamemode][reg_settings.mode],
        reverse=False,
    )
    players["add_up"].sort(
        key=lambda x: 10
        if x.division[gamemode][reg_settings.mode] == -1
        else x.division[gamemode][reg_settings.mode],
        reverse=False,
    )
    all_players = players["next_pug"] + players["add_up"]

    red_team: list[PugPlayer] = []
    blu_team: list[PugPlayer] = []
    count = 0

    while len(red_team) < team_size and len(blu_team) < team_size:
        if count % 2 == 0:
            red_team.append(all_players.pop(0))
            blu_team.append(all_players.pop(0))
        else:
            blu_team.append(all_players.pop(0))
            red_team.append(all_players.pop(0))
        count += 1

    teams = {"red": red_team, "blu": blu_team}
    return teams


async def generate_elo_teams(
    players: Dict[str, List[PugPlayer]],
    team_size: int,
) -> Dict[str, List[PugPlayer]]:
    """Generate balanced teams for a pug.

    Args:
        players (dict): A dictionary of all players in the VCs
        team_size (int): The amount of players per team.
        reg_settings (RegistrationSettings): The registration settings for the server.

    Returns:
        teams: The generated teams.
    """
    random.shuffle(players["next_pug"])
    random.shuffle(players["add_up"])
    all_players = players["next_pug"] + players["add_up"]

    red_team: List[PugPlayer] = []
    blu_team: List[PugPlayer] = []

    total_elo: int = 0
    all_elos: List[int] = []
    elo_players: List[PugPlayer] = []
    for player in all_players[0 : team_size * 2]:
        player_elo = await get_elo(discord=player.discord)
        all_elos.append(player_elo.elo)  # TODO: Change to use server settings
    print(elo_players)

    # Add additive to all elos
    cardinality = len(all_elos)
    max_num = max(all_elos)
    additive = cardinality * max_num
    for player in all_players[0 : team_size * 2]:
        player_elo = await get_elo(discord=player.discord)
        print(player_elo.as_dict())
        player.elo = player_elo.elo + additive
        total_elo += player.elo
        elo_players.append(player)

    # Find balanced teams
    if team_size > 1:
        try:
            red_team = find_subset(elo_players, int(total_elo / 2))
            blu_team = elo_players.copy()
        except ValueError:
            try:
                tolerance = (max(all_elos) - min(all_elos)) / 2
                red_team = find_subset(
                    elo_players, int(total_elo / 2), tolerance=int(tolerance)
                )
                blu_team = elo_players.copy()
            except ValueError:
                red_team = list(elo_players[0:team_size])
                blu_team = list(elo_players[team_size : team_size * 2])
    else:
        red_team = [elo_players[0]]
        blu_team = [elo_players[1]]
    for item in red_team:
        for i, item_blu in enumerate(blu_team):
            if item_blu.discord == item.discord:
                blu_team.pop(i)
                break

    for i in range(0, team_size):
        red_team[i].elo = red_team[i].elo - additive
        blu_team[i].elo = blu_team[i].elo - additive

    teams = {"red": red_team, "blu": blu_team}
    return teams


def find_subset(
    arr: List[PugPlayer], total: int, tolerance: int = 1
) -> List[PugPlayer]:
    """Find a subset of a list that adds up to a total.

    Args:
        arr (List[EloPlayer]): The list of all players
        total (int): The total elo of the teams

    Raises:
        ValueError: Subset not found

    Returns:
        List[EloPlayer]: One subset of players that adds up to the total elo
    """
    if (tolerance * -1) <= total <= tolerance:
        return arr
    if arr is None:
        raise ValueError("Subset not found")
    for item in arr:
        new_arr: List = arr.copy()
        new_arr.remove(item)
        new_sum = total - item.elo
        if new_sum < 0:
            continue
        if find_subset(new_arr, new_sum) is not None:
            return find_subset(new_arr, new_sum)
        continue
    raise ValueError("Subset not found")


class PugRunningCog(commands.Cog):
    """Cog storing all the commands to run pugs"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @nextcord.slash_command()
    async def pug(self, interaction: nextcord.Interaction):
        """
        This is the main slash command that will be the prefix of all commands below.
        This will never get called since it has subcommands.
        """

    @pug.subcommand(  # pylint: disable=no-member
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

        if team_size is None:
            team_size = 6

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
            try:
                if (
                    len(add_up_channel.members) + len(next_pug_channel.members)
                ) < team_size * 2:
                    disabled = True
                    name += " (Not enough players)"
                if (
                    len(red_team_channel.members) > 0
                    or len(blu_team_channel.members) > 0
                ):
                    disabled = True
                    name += " (Pug in progress)"
                if (
                    interaction.user.voice is not None
                    and interaction.user.voice.channel
                    == (next_pug_channel or add_up_channel)
                ):
                    color = nextcord.ButtonStyle.green
            except AttributeError:
                print(f"Error getting channels for {name}")
                name += " (Error getting channels)"
                disabled = True

                button = CategoryButton(name=name, color=color, disabled=disabled)
                select_view.add_item(button)
                continue

            button = CategoryButton(name=name, color=color, disabled=disabled)
            select_view.add_item(button)

        pug_embed = nextcord.Embed(
            title="Generate Teams",
            color=BOT_COLOR,
            description="Select the category you would like to generate teams for.",
        )
        await interaction.send(embed=pug_embed, view=select_view)
        embed_status = await select_view.wait()
        if embed_status or select_view.name == "cancel":
            return

        chosen_category: PugCategory = PugCategory(
            select_view.name, categories[select_view.name]
        )

        add_up: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.add_up
        )
        red_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.red_team
        )
        blu_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.blu_team
        )
        next_pug: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.next_pug
        )

        pug_embed.description = None
        balancing_disabled = False
        elo_enabled = False  # pylint: disable=unused-variable
        # TODO: Implement this ^
        elo_used = False

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

        teams = await generate_balanced_teams(
            await get_player_dict(next_pug, add_up), team_size, reg_settings
        )

        while True:
            team_generation_view = TeamGenerationView(balancing_disabled)
            if not elo_used:
                if not balancing_disabled:
                    teams["red"].sort(
                        key=lambda x: x.division[gamemode][reg_settings.mode],
                        reverse=False,
                    )
                red_team_string = ""
                red_level = 0
                red_count = 0
                for player in teams["red"]:
                    if balancing_disabled:
                        division = "?"
                    else:
                        if player.division[gamemode][reg_settings.mode] == -1:
                            division = "?"
                        else:
                            division = str(player.division[gamemode][reg_settings.mode])
                            red_level += player.division[gamemode][reg_settings.mode]
                            red_count += 1
                    red_team_string += f"[{division}] <@{player.discord}>\n"

                if not balancing_disabled:
                    teams["blu"].sort(
                        key=lambda x: x.division[gamemode][reg_settings.mode],
                        reverse=False,
                    )
                blu_team_string = ""
                blu_level = 0
                blu_count = 0
                for player in teams["blu"]:
                    if balancing_disabled:
                        divison = "?"
                    else:
                        if player.division[gamemode][reg_settings.mode] == -1:
                            divison = "?"
                        else:
                            divison = str(player.division[gamemode][reg_settings.mode])
                            blu_level += player.division[gamemode][reg_settings.mode]
                            blu_count += 1
                    blu_team_string += f"[{divison}] <@{player.discord}>\n"

                pug_embed.clear_fields()
                if red_count != 0 and blu_count != 0:
                    pug_embed.add_field(
                        name=f"🔴 Red Team\nLevel: {(red_level / red_count):.2f}",
                        value=red_team_string,
                    )
                    pug_embed.add_field(
                        name=f"🔵 Blu Team\nLevel: {(blu_level / blu_count):.2f}",
                        value=blu_team_string,
                    )
                else:
                    pug_embed.add_field(name="🔴 Red Team", value=red_team_string)
                    pug_embed.add_field(name="🔵 Blu Team", value=blu_team_string)
            else:
                red_team_elo = 0
                red_team_string = ""
                for elo_player in teams["red"]:
                    red_team_elo += elo_player.elo
                    red_team_string += (
                        f"[**{elo_player.elo}**] <@{elo_player.discord}>\n"
                    )
                blu_team_elo = 0
                blu_team_string = ""
                for elo_player in teams["blu"]:
                    blu_team_elo += elo_player.elo
                    blu_team_string += (
                        f"[**{elo_player.elo}**] <@{elo_player.discord}>\n"
                    )
                pug_embed.clear_fields()
                pug_embed.add_field(
                    name=f"🔴 Red Team\nElo: {round(red_team_elo/team_size)}",
                    value=red_team_string,
                )
                pug_embed.add_field(
                    name=f"🔵 Blu Team\nElo: {round(blu_team_elo/team_size)}",
                    value=blu_team_string,
                )

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
                    member = await interaction.guild.fetch_member(player.discord)
                    try:
                        await member.move_to(red_team)
                    except nextcord.HTTPException:
                        await interaction.send(
                            f"<@{player.discord}> could not be moved to the RED team."
                        )

                for player in teams["blu"]:
                    member = await interaction.guild.fetch_member(player.discord)
                    try:
                        await member.move_to(blu_team)
                    except nextcord.HTTPException:
                        await interaction.send(
                            f"<@{player.discord}> could not be moved to the BLU team."
                        )
                pug_embed.description = "Done moving players!"
                await interaction.edit_original_message(embed=pug_embed, view=None)

                # Add last players to db
                all_players = teams["red"] + teams["blu"]
                await chosen_category.update_last_players(
                    interaction.guild.id, all_players
                )

                game_players = [
                    Player(discord=player.discord) for player in all_players
                ]
                await LogSearcher.add_searcher_game(
                    interaction.guild.id, chosen_category, game_players
                )

                break

            if team_generation_view.action == "random":
                elo_used = False
                pug_embed.clear_fields()
                teams = await generate_random_teams(
                    await get_player_dict(next_pug, add_up), team_size
                )

            if team_generation_view.action == "elo":
                elo_used = True
                pug_embed.clear_fields()
                teams = await generate_elo_teams(
                    await get_player_dict(next_pug, add_up), team_size
                )

            if team_generation_view.action == "balanced":
                elo_used = False
                pug_embed.clear_fields()
                teams = await generate_balanced_teams(
                    await get_player_dict(next_pug, add_up),
                    team_size,
                    reg_settings,
                )

    async def get_player_list(
        self, next_pug: nextcord.VoiceChannel, add_up: nextcord.VoiceChannel
    ) -> Dict[str, List[PugPlayer]]:
        """Return a list of players in a voice channel.

        Args:
            channel (nextcord.VoiceChannel): The voice channel to get players from.

        Returns:
            list: A list of players in the voice channel.
        """
        players: Dict[str, list[PugPlayer]] = {"next_pug": [], "add_up": []}
        for member in next_pug.members:
            player = PugPlayer(discord=member.id)
            players["next_pug"].append(player)
        for member in add_up.members:
            player = PugPlayer(discord=member.id)
            players["add_up"].append(player)
        return players

    @pug.subcommand(  # pylint: disable=no-member
        name="move", description="Moves players after a pug is done."
    )
    @is_setup()
    @is_runner()
    async def move(
        self, interaction: nextcord.Interaction
    ):  # pylint: disable=too-many-return-statements
        """Move players back after a pug is done."""
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

            try:
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
            except AttributeError:
                print(f"Error getting channels for {name}")
                name += " (Error getting channels)"
                disabled = True

                button = CategoryButton(name=name, color=color, disabled=disabled)
                select_view.add_item(button)
                continue

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

        chosen_category: PugCategory = PugCategory(
            select_view.name, categories[select_view.name]
        )

        add_up: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.add_up
        )
        red_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.red_team
        )
        blu_team: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.blu_team
        )
        next_pug: nextcord.VoiceChannel = interaction.guild.get_channel(
            chosen_category.next_pug
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
            try:
                await member.move_to(next_pug)
            except nextcord.HTTPException:
                continue
        moving_string += (
            f"\nDone!\n\nMoving players from <#{red_team.id}> to <#{add_up.id}>..."
        )
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=None)
        for member in red_team.members:
            red_players.append(member)
            try:
                await member.move_to(add_up)
            except nextcord.HTTPException:
                continue
        moving_string += (
            f"\nDone!\n\nMoving players from <#{blu_team.id}> to <#{add_up.id}>..."
        )
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=None)
        for member in blu_team.members:
            blu_players.append(member)
            try:
                await member.move_to(add_up)
            except nextcord.HTTPException:
                continue
        moving_string += "\nDone!"

        game_players = [
            Player(discord=player.id) for player in red_players + blu_players
        ]
        # Check if game was already added to searcher
        genned: bool = True
        last_players: list[PugPlayer]
        timestamp: int
        last_players, timestamp = await chosen_category.get_last_players(
            interaction.guild.id
        )
        print(last_players)
        for player in last_players:
            if player.discord not in [
                int(player.id) for player in red_players + blu_players
            ]:
                genned = False
                break
        if not genned:
            print("Adding game to searcher...")
            await LogSearcher.add_searcher_game(
                interaction.guild.id, chosen_category, game_players, timestamp
            )

        move_view = MoveView()
        pug_embed.title = "Players moved!"
        pug_embed.description = moving_string
        await interaction.edit_original_message(embed=pug_embed, view=move_view)
        status = await move_view.wait()
        if status:
            await interaction.delete_original_message(delay=5)
            return

        if move_view.action == "cancel":
            return
        if move_view.action == "move":
            moving_string = f"Moving players from <#{next_pug.id}> to <#{add_up.id}>..."
            pug_embed.title = "Moving players back..."
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in waiting_players:
                try:
                    await member.move_to(add_up)
                except nextcord.HTTPException:
                    continue
            moving_string += (
                f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{red_team.id}>..."
            )
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in red_players:
                try:
                    await member.move_to(red_team)
                except nextcord.HTTPException:
                    continue
            moving_string += (
                f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{blu_team.id}>..."
            )
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)
            for member in blu_players:
                try:
                    await member.move_to(blu_team)
                except nextcord.HTTPException:
                    continue
            moving_string += "\nDone!"

            pug_embed.title = "Done moving players back."
            pug_embed.description = moving_string
            await interaction.edit_original_message(embed=pug_embed, view=None)

            await interaction.delete_original_message(delay=10)
            return

        await interaction.delete_original_message(delay=10)
