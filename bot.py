"""Main file for running and starting the bot, with general global commands."""

import datetime
import logging
import random
import re
from typing import Optional

import nextcord
from nextcord.ext import commands, tasks
from nextcord.ui import RoleSelect

import database
from constants import BOT_COLOR, DISCORD_TOKEN, NEW_COMMIT_NAME, VERSION
from logs.elo_cog import EloCog
from logs.logs import LogsCog
from logs.searcher import LogSearcher
from logs.stats import StatsCog
from menus import BotMenu
from menus.templates import send_channel_prompt
from pug.manual import ManualPugCog
from pug.med_immunity import PugMedicCog
from pug.pug import PugRunningCog
from pug.setup import PugSetupCog
from registration.registration import RegistrationCog
from registration.setup import RegistrationSetupCog
from registration.update_roles import UpdateRolesCog
from registration.webserver import Webserver
from rglapi import Player, RglApi, Team
from servers.servers import ServerCog
from test_cog import TestCog
from util import get_steam64

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

activity = nextcord.Activity(name="pugBot.tf :3", type=nextcord.ActivityType.watching)
bot: commands.Bot = commands.Bot(intents=intents, activity=activity)

bot.add_cog(
    TestCog(bot)
)  # Keep this Cog at the top as the test command might need to be loaded first
bot.add_cog(RegistrationSetupCog(bot))
bot.add_cog(PugSetupCog(bot))
bot.add_cog(PugRunningCog(bot))
bot.add_cog(PugMedicCog(bot))
bot.add_cog(LogsCog(bot))
bot.add_cog(EloCog(bot))
bot.add_cog(StatsCog(bot))
manual_cog: ManualPugCog = ManualPugCog(bot)
bot.add_cog(manual_cog)
bot.remove_command("help")

RGL: RglApi = RglApi()

logging.basicConfig(level=logging.INFO)


@bot.event
async def on_ready() -> None:
    """Prints bot information on ready, starts webserver, and syncs commands."""
    if bot.user is not None:
        logging.info("Logged in as %s (ID: %d)", bot.user.name, bot.user.id)
        logging.info("Running: %s", NEW_COMMIT_NAME)
        logging.info("------")
    logging.info("Creating webserver...")
    registration_cog: RegistrationCog = RegistrationCog(bot)
    bot.add_cog(registration_cog)
    webserver: Webserver = Webserver(registration_cog)
    logging.info("Adding delayed cogs...")
    bot.add_cog(UpdateRolesCog(bot))
    bot.add_cog(ServerCog(bot))
    logging.info("Syncing commands...")
    await bot.sync_all_application_commands()
    logging.info("Starting bot loops...")
    update_status.start()
    manual_cog.status_check.start()  # pylint: disable=no-member
    manual_cog.update_channel_status.start()  # pylint: disable=no-member
    log_searcher: LogSearcher = LogSearcher(bot)
    log_searcher.searcher.start()  # pylint: disable=no-member
    log_searcher.queue.start()  # pylint: disable=no-member
    logging.info("Starting webserver. Bot is ready!")
    await registration_cog.start_server(webserver.app)


@bot.slash_command(
    name="setup",
    description="Setup the bot for this server.",
    default_member_permissions=nextcord.Permissions(manage_guild=True),
)
async def setup(interaction: nextcord.Interaction):
    """The /setup command, used to setup the bot for a guild.

    Args:
        interaction (nextcord.Interaction): The interaction to respond to.
    """
    if interaction.guild is None:
        await interaction.send(
            "This command can only be used in a server.", ephemeral=True
        )
        return
    if not isinstance(interaction.user, nextcord.Member):
        return

    setup_embed = nextcord.Embed(
        title="Initial Bot Setup",
        description="Select a role to be used as the Runner role. This role has permissions to generate teams, move players, and more commands with the bot.",
        color=BOT_COLOR,
    )
    menu: BotMenu = BotMenu(user_id=interaction.user.id, embed=setup_embed)
    if menu.embed is None:
        return
    role_select: RoleSelect = RoleSelect(max_values=1, placeholder="Select a role")
    menu.add_item(role_select)
    await menu.add_continue_buttons()
    await menu.send(interaction)
    if not await menu.wait_for_action(bot) or menu.action == "cancel":
        await interaction.delete_original_message()
        return

    if len(role_select.values) == 0:
        await interaction.edit_original_message(
            content="You must select a Runner role.", embed=None, view=None
        )
        await interaction.delete_original_message(delay=30)
        return
    selected_role: nextcord.Role = role_select.values[0]

    menu.embed.description = "Select channels to be used as the connect and rcon channel.\nYou do not have to select channels if you are not planning to reserve servers with the bot."
    try:
        selected_channels = await send_channel_prompt(
            menu,
            interaction,
            ["Connect Channel", "RCON Channel"],
            False,
            [nextcord.ChannelType.text],
        )
    except TimeoutError:
        await interaction.delete_original_message()
        return

    menu.embed.title = "Setup Complete!"
    menu.embed.description = (
        "Setup has been completed for this server. You can now use the bot's commands."
    )
    menu.embed.color = nextcord.Color.green()

    connect_id: int | None = (
        None if selected_channels[0] is None else selected_channels[0].id
    )
    rcon_id: int | None = (
        None if selected_channels[1] is None else selected_channels[1].id
    )
    menu.embed.add_field(
        name="Runner Role", value=f"<@&{selected_role.id}>", inline=True
    )
    menu.embed.add_field(name="Connect Channel", value=f"<#{connect_id}>", inline=True)
    menu.embed.add_field(name="RCON Channel", value=f"<#{rcon_id}>", inline=True)
    await interaction.edit_original_message(content=None, embed=menu.embed, view=None)
    await database.add_new_guild(
        interaction.guild.id, selected_role.id, connect_id, rcon_id
    )


@bot.slash_command(
    name="serveme",
    description="Set the serveme api key for this server.",
    default_member_permissions=nextcord.Permissions(manage_guild=True),
)
async def serveme(interaction: nextcord.Interaction, api_key: str):
    """The /serveme command, used to set the serveme api key for a guild.

    Args:
        interaction (nextcord.Interaction): The interaction to respond to.
        api_key (str): The api key to set.
    """
    if interaction.guild is None:
        await interaction.send(
            "This command can only be used in a server.", ephemeral=True
        )
        return
    await database.set_guild_serveme(interaction.guild.id, api_key)
    await interaction.send("Serveme API Key set!", ephemeral=True)


async def create_player_embed(player: Player) -> nextcord.Embed:
    """Creates a embed to represent an RGL player.

    Args:
        player (Player): The player to create the embed for.

    Returns:
        embed (nextcord.Embed): The embed to represent the player.
    """
    if not player.bans[0]:
        embed_color = 0xF0984D
    else:
        embed_color = 0xFF0000

    url = "https://rgl.gg/Public/PlayerProfile.aspx?p=" + str(player.steamid)

    embed = nextcord.Embed(title=player.name, url=url, color=embed_color)
    embed.set_thumbnail(url=player.pfp)
    if player.sixes != []:  # Sixes Data
        sixes_teams = ""
        for season in player.sixes:
            if season["division"].startswith("RGL-"):
                season["division"] = season["division"][4:]
            sixes_teams += (
                f"{season['season']} - {season['division']} - {season['team']}\n"
            )

        embed.add_field(name="Sixes", value=sixes_teams, inline=False)
    if player.highlander != []:  # HL Data
        hl_teams = ""
        for season in player.highlander:
            if season["division"].startswith("RGL-"):
                season["division"] = season["division"][4:]
            hl_teams += (
                f"{season['season']} - {season['division']} - {season['team']}\n"
            )
        embed.add_field(name="Highlander", value=hl_teams, inline=False)
    if player.bans[0]:  # Ban Info
        embed.add_field(name="Currently Banned", value=player.bans[1], inline=False)

    embed.set_footer(text=VERSION)
    return embed


async def create_team_embed(team: Team) -> nextcord.Embed:
    """Creates an embed to represent an RGL team.

    Args:
        team (Team): The team to create the embed for.

    Returns:
        embed (nextcord.Embed): The embed to represent the team.
    """

    if team.current_players:
        embed_color = 0xCCCCDC
    else:
        embed_color = 0xFEF0C7

    url = "https://rgl.gg/Public/Team?t=" + str(team.team_id)

    embed = nextcord.Embed(title=team.name, url=url, color=embed_color)

    embed.add_field(name=team.tag, value="", inline=True)
    if team.rank:
        embed.add_field(name="Team Rank", value=team.rank, inline=True)

    embed.add_field(name=team.season_name, value=team.division, inline=False)

    player_text = ""
    for player in team.current_players:
        player_text += "["
        if player["isLeader"]:
            player_text += ":star: "
        player_text += (
            player["name"]
            + f"""](https://rgl.gg/Public/PlayerProfile?p={player["steamId"]})\n"""
        )
    if player_text:
        embed.add_field(name="Current Players", value=player_text, inline=False)

    player_text = ""
    for player in team.former_players:
        player_text += "["
        if player["isLeader"]:
            player_text += ":star: "
        player_text += (
            player["name"]
            + f"""](https://rgl.gg/Public/PlayerProfile?p={player["steamId"]})\n"""
        )
    if player_text:
        embed.add_field(name="Former Players", value=player_text, inline=False)

    embed.set_footer(text=VERSION)
    return embed


@bot.listen("on_message")
async def rgl_link_listener(message: nextcord.Message):
    """Listener for messages that contain a link to a player's RGL profile or to a RGL team page.

    Args:
        message (nextcord.Message): The message to check.
    """
    if "https://rgl.gg/Public/PlayerProfile?" in message.content:
        regex = re.search(
            r"(?<=https:\/\/rgl\.gg\/Public\/PlayerProfile\?p=)[0-9]*",
            message.content,
        )
        if regex is None:
            return
        player = await RGL.create_player(int(get_steam64(regex.group(0))))
        embed = await create_player_embed(player)
        await message.channel.send(embed=embed)
    elif "https://rgl.gg/Public/Team?" in message.content:
        regex = re.search(
            r"(?<=https:\/\/rgl\.gg\/Public\/Team\?t=)[0-9]*",
            message.content,
        )
        print(regex)
        if regex is None:
            return
        team_id = int(regex.group(0))
        team = await RGL.create_team(team_id)
        embed = await create_team_embed(team)
        await message.channel.send(embed=embed)


@bot.slash_command(
    name="search", description="Search for an RGL profile and display it."
)
async def search(
    interaction: nextcord.Interaction,
    discord_user: Optional[nextcord.User] = nextcord.SlashOption(
        name="discord", description="The user to look up.", required=False
    ),
    steamid: Optional[str] = nextcord.SlashOption(
        name="steam", description="The steam ID to look up.", required=False
    ),
):
    """Search for a players RGL profile and generate the embed.

    Args:
        interaction (nextcord.Interaction): The interaction to respond to.
        discord_user (User): The player to search for
        steamid (str): The player to search for.
    """
    await interaction.response.defer()
    if discord_user is not None:
        steam_id = await database.get_steam_from_discord(discord_user.id)
        if steam_id is None:
            await interaction.send(
                "User is not registered in the bot's database.",
                ephemeral=True,
            )
            return
        rgl = await RGL.create_player(int(get_steam64(steam_id)))
    elif steamid is not None:
        rgl = await RGL.create_player(int(get_steam64(steamid)))
    else:
        await interaction.send("You must specify a user or steam ID.", ephemeral=True)
        return
    embed = await create_player_embed(rgl)
    await interaction.send(embed=embed)


@bot.slash_command(
    name="help", description="Displays all the bots commands and their purpose."
)
async def help_command(interaction: nextcord.Interaction):
    """The /help command, explains all the commands the bot has.

    Args:
        interaction (nextcord.Interaction): The interaction that invoked the command.
    """
    help_embed = nextcord.Embed(
        title="pugBot Commands",
        url="https://github.com/Ooglely/pugBot",
        color=BOT_COLOR,
    )
    help_embed.set_thumbnail("https://ooglely.github.io/53EWxbz.jpeg")
    help_embed.add_field(
        name="Global Commands",
        value="/setup - Used to setup the bot for a guild (Admin only)\n/serveme - Used to set the serveme api key for a guild (Admin only)\n/registration - Sets up pugBot.tf registration (Admin only)\n/register - Registers a player in the bot's database\n/search - Search for a player's RGL profile\n/reserve - Get a new reservation from na.serveme.tf\n/map - Change the map on a running reservation\n/rcon - Run an rcon command on an active reservation",
        inline=False,
    )
    help_embed.set_footer(text=VERSION)
    await interaction.send(embed=help_embed)


@bot.listen("on_message")
async def respond_to_mentions(message: nextcord.Message):
    """just playing around

    Args:
        message (nextcord.Message): The message to check.
    """
    if not isinstance(message.author, nextcord.Member) or not message.guild:
        return  # Don't respond to DMs
    if "<@989250144895655966>" in message.content:
        seed = random.random()
        if message.author.voice is not None:
            if seed < 0.2:
                await message.channel.send(
                    "dude aren't you literally pugging right now stop annoying me"
                )
                return
        if seed < 0.1:
            await message.channel.send(
                "Dude I'm serious. Stop pinging me or there will be consequences."
            )
            if message.guild.id == 1144719525728763915:
                # Get member and timeout
                timeout_time = datetime.datetime.now() + datetime.timedelta(seconds=30)
                await message.author.timeout(timeout_time, reason="hahahahahaha")
        elif seed < 0.2:
            await message.channel.send(
                "lol what do u want dude i bet u don't even hit 200 dpm stop pinging me"
            )
        elif seed < 0.3:
            await message.channel.send("what!!!! what do u want!!!!!")
        elif seed < 0.4:
            await message.channel.send("cu@lan buddy")
        elif seed < 0.6:
            await message.channel.send("i'm literally just an otter what do u want")
        else:
            await message.channel.send("what do u want dude lol")


@tasks.loop(minutes=1)
async def update_status():
    """Updates the bot's status with various data."""
    statuses = [
        f"{len(bot.guilds)} guilds",
        "pugBot.tf :3",
        f"{len(bot.users)} users",
        "sea otters :D",
        f"{await database.player_count()} registered players",
        "meds drop :(",
        f"{await database.log_count()} recorded logs",
    ]
    await bot.change_presence(
        activity=nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name=random.choice(statuses),
        )
    )


bot.run(DISCORD_TOKEN)
