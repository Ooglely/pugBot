"""Commands for generating teams in pugs."""

from itertools import combinations
import random
import time
from typing import Optional, Dict, List

import nextcord
from nextcord.ext import commands

from constants import BOT_COLOR
from database import BotCollection
from logs import Player
from logs.searcher import LogSearcher
from logs.elo import get_elo, Elo
from logs.elo_cog import EloSettings
from menus import BotMenu
from menus.callbacks import action_callback
from menus.templates import TeamGenMenu
from pug import (
    CategorySelect,
    CategoryButton,
    PugPlayer,
    PugCategory,
    Teams,
)

from registration import RegistrationSettings
from util import is_runner, guild_config_check

category_db = BotCollection("guilds", "categories")
config_db = BotCollection("guilds", "config")


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
        player = await PugPlayer.create(discord=member.id)
        players["next_pug"].append(player)
    for member in add_up.members:
        player = await PugPlayer.create(discord=member.id)
        players["add_up"].append(player)
    return players


async def generate_random_teams(
    players: Dict[str, List[PugPlayer]], team_size: int
) -> Teams:
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

    if len(all_players) < team_size * 2:
        raise ValueError(
            "Not enough players to generate teams. "
            f"Required: {team_size * 2}, Available: {len(all_players)}"
        )

    while len(red_team) < team_size and len(blu_team) < team_size:
        red_team.append(all_players.pop(0))
        blu_team.append(all_players.pop(0))

    teams = Teams(red=red_team, blu=blu_team)
    return teams


async def generate_balanced_teams(
    players: Dict[str, List[PugPlayer]],
    team_size,
    reg_settings: RegistrationSettings,
    gamemode: str,
) -> Teams:
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

    random.shuffle(players["next_pug"])
    random.shuffle(players["add_up"])
    # Deprioritize players that are not registered, as their skill is unknown
    players["next_pug"].sort(
        key=lambda x: (
            10
            if x.get_division(gamemode, reg_settings.mode) == -1
            else x.get_division(gamemode, reg_settings.mode)
        ),
        reverse=False,
    )
    players["add_up"].sort(
        key=lambda x: (
            10
            if x.get_division(gamemode, reg_settings.mode) == -1
            else x.get_division(gamemode, reg_settings.mode)
        ),
        reverse=False,
    )
    all_players = players["next_pug"] + players["add_up"]

    if len(all_players) < team_size * 2:
        raise ValueError(
            "Not enough players to generate teams. "
            f"Required: {team_size * 2}, Available: {len(all_players)}"
        )

    total_level: int = 0
    team_players: List[PugPlayer] = []
    for player in all_players[0 : team_size * 2]:
        if player.get_division(gamemode, reg_settings.mode) == -1:
            player.elo = 0
        else:
            player.elo = player.get_division(gamemode, reg_settings.mode)
        team_players.append(player)
        total_level += player.elo

    teams = await process_players(team_players, team_size, int(total_level / 2))
    return teams


async def generate_elo_teams(
    players: Dict[str, List[PugPlayer]],
    team_size: int,
    elo_settings: EloSettings,
    category: PugCategory,
) -> Teams:
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

    if len(all_players) < team_size * 2:
        raise ValueError(
            "Not enough players to generate teams. "
            f"Required: {team_size * 2}, Available: {len(all_players)}"
        )

    total_elo: int = 0
    elo_players: List[PugPlayer] = []

    for player in all_players[0 : team_size * 2]:
        try:
            player_elo = await get_elo(discord=player.discord)
        except LookupError:
            player_elo = Elo(0)  # default elo value
        print(player_elo.as_dict())
        player.elo = await player_elo.get_elo_from_mode(
            elo_settings.mode, elo_settings.guild_id, category.name, team_size
        )
        total_elo += player.elo
        elo_players.append(player)

    teams = await process_players(elo_players, team_size, int(total_elo / 2))
    return teams


async def generate_role_teams(
    players: Dict[str, List[PugPlayer]],
    team_size: int,
    guild: nextcord.Guild,
    roles: Dict[str, Dict],
) -> Teams:
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

    if len(all_players) < team_size * 2:
        raise ValueError(
            "Not enough players to generate teams. "
            f"Required: {team_size * 2}, Available: {len(all_players)}"
        )

    total_value: int = 0
    processed_players: List[PugPlayer] = []

    sorted_roles = sorted(roles.items(), key=lambda x: x[1]["value"], reverse=True)

    for player in all_players[0 : team_size * 2]:
        # Check for first role player has
        member = await guild.fetch_member(player.discord)
        for role in sorted_roles:
            if int(role[0]) in [role.id for role in member.roles]:
                player.elo = role[1]["value"]
                player.icon = role[1]["icon"]
                total_value += role[1]["value"]
                break
        if not player.elo:
            player.elo = 0
        processed_players.append(player)

    teams = await process_players(processed_players, team_size, int(total_value / 2))
    return teams


async def process_players(
    players: List[PugPlayer], team_size: int, target_elo: int
) -> Teams:
    """Turn a list of players into two balanced teams.

    Args:
        players (List[PugPlayer]): A list of the players to process
        team_size (int): The size of the teams
        target_elo (int): The target elo for each team

    Returns:
        Dict[str, List[PugPlayer]]: The two teams
    """
    red_team = find_subset(players, team_size, target_elo)
    blu_team = players.copy()

    # Remove players from blu team
    for item in red_team:
        for i, item_blu in enumerate(blu_team):
            if item_blu.discord == item.discord:
                blu_team.pop(i)
                break

    return Teams(red=red_team, blu=blu_team)


def find_subset(arr: List[PugPlayer], num: int, goal: int) -> List[PugPlayer]:
    """Find a subset of players of size num that gets as close to total as possible.

    Args:
        arr (List[EloPlayer]): The list of all players
        num (int): Team size
        goal (int): The target average ELO for each team

    Raises:
        ValueError: Subset not found

    Returns:
        List[EloPlayer]: One subset of players that is closest to the total elo
    """
    # Find every UNIQUE subset of arr of size num
    # Get initial lowest diff
    lowest_diff = 0
    for player in arr[0:num]:
        lowest_diff += player.elo
    if lowest_diff == 0:
        lowest_diff = 9999  # lol weird workaround but its needed

    best_team: List[PugPlayer] = arr[0:num]
    result = combinations(arr, num)
    for combination in result:
        team_total = 0
        for player in combination:
            team_total += player.elo
        if abs(goal - team_total) < lowest_diff:
            lowest_diff = abs(goal - team_total)
            best_team = list(combination)
        if lowest_diff == 0:
            break
    return best_team


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
    @guild_config_check()
    @is_runner()
    async def genteams(
        self,
        interaction: nextcord.Interaction,
        team_size: Optional[int | None] = nextcord.SlashOption(
            name="team_size",
            description="The amount of players per team.",
            required=False,
        ),
    ):
        """Generate teams for a pug."""
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.response.send_message(
                "This command must be run in a server.", ephemeral=True
            )
            return
        if interaction.user is None:
            await interaction.response.send_message(
                "This command must be run by a user.", ephemeral=True
            )
            return

        balancing_disabled: bool = False
        role_disabled: bool = False
        elo_disabled: bool = True
        mode: str = ""

        try:
            guild_config = await config_db.find_item({"guild": interaction.guild.id})
            roles = guild_config["roles"]
        except (LookupError, KeyError):
            role_disabled = True

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
            if "manual" in guild_config:
                team_size = int((guild_config["manual"]["num_players"]) / 2)
            else:
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

        reg_settings = RegistrationSettings()
        await reg_settings.load_data(interaction.guild.id)
        if not reg_settings.enabled:
            balancing_disabled = True

        elo_settings = EloSettings(interaction.guild.id)
        await elo_settings.load()
        if elo_settings.enabled:
            elo_disabled = False
        else:
            pug_embed.set_footer(
                text="Elo is disabled for this server, enable using /elo setup!"
            )

        teams: Teams
        if not elo_disabled:
            teams = await generate_elo_teams(
                await get_player_dict(next_pug, add_up),
                team_size,
                elo_settings,
                chosen_category,
            )
            mode = "elo"
        elif not balancing_disabled:
            mode = reg_settings.gamemode if reg_settings.gamemode != "both" else "sixes"
            teams = await generate_balanced_teams(
                await get_player_dict(next_pug, add_up), team_size, reg_settings, mode
            )
        elif not role_disabled:
            guild = await self.bot.fetch_guild(interaction.guild.id)
            teams = await generate_role_teams(
                await get_player_dict(next_pug, add_up), team_size, guild, roles
            )
            mode = "roles"
        else:
            teams = await generate_random_teams(
                await get_player_dict(next_pug, add_up), team_size
            )
            mode = "random"

        pug_embed.title = "Generate Teams"
        gen_menu = TeamGenMenu(
            interaction.user.id,
            pug_embed,
            reg_settings,
            not elo_disabled,
            not role_disabled,
        )
        await gen_menu.add_gen_buttons()
        gen_menu.action = mode

        while True:  # Loop while teams are being generated
            await gen_menu.update_teams(teams)
            await gen_menu.edit(interaction)
            view_result = await gen_menu.wait_for_action(self.bot)
            if not view_result:
                await interaction.delete_original_message(delay=5)
                return
            match gen_menu.action:
                case "move":
                    # Move players to the correct channels
                    pug_embed.description = "Moving players.."
                    await interaction.edit_original_message(embed=pug_embed, view=None)
                    pug_embed.description = ""

                    for player in teams["red"]:
                        member = await interaction.guild.fetch_member(player.discord)
                        try:
                            await member.move_to(red_team)
                        except nextcord.HTTPException:
                            pug_embed.description += f"<@{player.discord}> could not be moved to the RED team.\n"

                    for player in teams["blu"]:
                        member = await interaction.guild.fetch_member(player.discord)
                        try:
                            await member.move_to(blu_team)
                        except nextcord.HTTPException:
                            pug_embed.description += f"<@{player.discord}> could not be moved to the BLU team.\n"
                    pug_embed.description += "Done moving players!"
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
                case "elo":
                    teams = await generate_elo_teams(
                        await get_player_dict(next_pug, add_up),
                        team_size,
                        elo_settings,
                        chosen_category,
                    )
                case "sixes" | "highlander" | "combined":
                    teams = await generate_balanced_teams(
                        await get_player_dict(next_pug, add_up),
                        team_size,
                        reg_settings,
                        gen_menu.action,
                    )
                case "roles":
                    teams = await generate_role_teams(
                        await get_player_dict(next_pug, add_up),
                        team_size,
                        interaction.guild,
                        roles,
                    )
                case "random":
                    teams = await generate_random_teams(
                        await get_player_dict(next_pug, add_up), team_size
                    )
                case "cancel":
                    await interaction.delete_original_message()
                    break

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
            player = await PugPlayer.create(discord=member.id)
            players["next_pug"].append(player)
        for member in add_up.members:
            player = await PugPlayer.create(discord=member.id)
            players["add_up"].append(player)
        return players

    @pug.subcommand(  # pylint: disable=no-member
        name="move", description="Moves players after a pug is done."
    )
    @guild_config_check()
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
        last_players: list[PugPlayer]
        old_timestamp: int
        player_matches: int = 0
        try:
            last_players, old_timestamp = await chosen_category.get_last_players(
                interaction.guild.id
            )
        except LookupError:
            last_players = []

        for player in last_players:
            if player.discord in [
                int(player.id) for player in red_players + blu_players
            ]:
                player_matches += 1

        if (not player_matches > (len(game_players) * 0.9)) or (
            round(time.time()) - old_timestamp > 21600
        ):
            # This pug was likely not generated by the bot so we should add it to the searcher
            timestamp = round(time.time()) - 7200
            print("Adding game to searcher...")
            await LogSearcher.add_searcher_game(
                interaction.guild.id, chosen_category, game_players, timestamp
            )

        pug_embed.title = "Players moved!"
        pug_embed.description = moving_string
        move_menu = BotMenu(interaction.user.id, pug_embed)
        move_menu.add_button(
            "Move Back", await action_callback("move", interaction.user.id)
        )
        move_menu.add_button(
            "Done",
            await action_callback("cancel", interaction.user.id),
            nextcord.ButtonStyle.green,
        )
        await move_menu.edit(interaction)
        menu_status = await move_menu.wait_for_action(self.bot)
        if not menu_status or move_menu.action == "cancel":
            await interaction.delete_original_message()
            return
        # Move players back
        move_menu.clear_items()
        moving_string = f"Moving players from <#{next_pug.id}> to <#{add_up.id}>..."
        pug_embed.title = "Moving players back..."
        pug_embed.description = moving_string
        await move_menu.edit(interaction)
        for member in waiting_players:
            try:
                await member.move_to(add_up)
            except nextcord.HTTPException:
                continue
        moving_string += (
            f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{red_team.id}>..."
        )
        pug_embed.description = moving_string
        await move_menu.edit(interaction)
        for member in red_players:
            try:
                await member.move_to(red_team)
            except nextcord.HTTPException:
                continue
        moving_string += (
            f"\nDone!\n\nMoving players from <#{add_up.id}> to <#{blu_team.id}>..."
        )
        pug_embed.description = moving_string
        await move_menu.edit(interaction)
        for member in blu_players:
            try:
                await member.move_to(blu_team)
            except nextcord.HTTPException:
                continue
        moving_string += "\nDone!"

        pug_embed.title = "Done moving players back."
        pug_embed.description = moving_string
        await move_menu.edit(interaction)
        await interaction.delete_original_message(delay=10)
