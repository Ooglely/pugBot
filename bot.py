"""Main file for running and starting the bot, with general global commands."""
import random
import re
from typing import Optional

import logging
import nextcord
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from nextcord.ext import commands, tasks

import database
from rgl_api import RGL_API, Player, Team
from constants import (
    BOT_COLOR,
    NEW_COMMIT_NAME,
    VERSION,
    DISCORD_TOKEN,
    TESTING_GUILDS,
    GITHUB_API_KEY,
    RAILWAY_API_KEY,
)
from util import get_steam64
from servers.servers import ServerCog
from agg.stats import StatsCog
from agg.pug import PugCog
from logs.searcher import LogSearcher
from pug.pug import PugRunningCog
from pug.setup import PugSetupCog
from registration.setup import RegistrationSetupCog
from registration.update_roles import UpdateRolesCog
from registration.webserver import WebserverCog

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

activity = nextcord.Activity(name="tf.oog.pw :3", type=nextcord.ActivityType.watching)
bot: nextcord.Client = commands.Bot(intents=intents, activity=activity)

bot.add_cog(ServerCog(bot))
bot.add_cog(StatsCog(bot))
bot.add_cog(PugCog(bot))
bot.add_cog(UpdateRolesCog(bot))
bot.add_cog(RegistrationSetupCog(bot))
bot.add_cog(PugSetupCog(bot))
bot.add_cog(PugRunningCog(bot))
bot.remove_command("help")

RGL: RGL_API = RGL_API()

logging.basicConfig(level=logging.INFO)


@bot.event
async def on_ready():
    """Prints bot information on ready, starts webserver, and syncs commands."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Running: {NEW_COMMIT_NAME}")
    print("------")
    # Need to add cog on ready instead of before for webserver async to be friendly
    bot.add_cog(WebserverCog(bot))
    await bot.sync_all_application_commands()
    update_status.start()
    log_searcher = LogSearcher(bot)
    log_searcher.searcher.start()  # pylint: disable=no-member
    log_searcher.queue.start()  # pylint: disable=no-member


class SetupView(nextcord.ui.View):
    """View for the 1st part of the /setup command, selecting a role."""

    def __init__(self):
        super().__init__()
        self.role = None

    @nextcord.ui.role_select(placeholder="Select a role", row=1)
    async def role(
        self, role: nextcord.ui.RoleSelect, interaction: nextcord.Interaction
    ):
        """Selects a role to be the runner role.

        Args:
            role (nextcord.ui.RoleSelect): The role to be the runner role.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.role = role.values[0].id
        self.stop()


class ChannelView(nextcord.ui.View):
    """View for the 2nd part of the /setup command, selecting channels."""

    def __init__(self):
        super().__init__()
        self.connect = None
        self.rcon = None

    @nextcord.ui.channel_select(
        custom_id="connect", placeholder="Select a connect channel"
    )
    async def connect(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel to send connect ip/link to.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.connect = channel.values[0].id
        if self.rcon is not None:
            self.stop()

    @nextcord.ui.channel_select(placeholder="Select a rcon channel")
    async def rcon(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        """Select a channel to send rcon commands to.

        Args:
            channel (nextcord.ui.ChannelSelect): The selected channel.
            interaction (nextcord.Interaction): The interaction to respond to.
        """
        await interaction.response.defer()
        self.rcon = channel.values[0].id
        if self.connect is not None:
            self.stop()


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
    setup_view = SetupView()
    channel_view = ChannelView()
    await interaction.send(
        "Select a role to be the runner role.", view=setup_view, ephemeral=True
    )
    await setup_view.wait()
    await interaction.edit_original_message(
        content="Select channels to be used as the connect and rcon channel.",
        view=channel_view,
    )
    await channel_view.wait()
    setup_embed = nextcord.Embed(
        title="Setup Complete!",
        description="Setup has been completed for this server. You can now use the bot's commands.",
        color=nextcord.Color.green(),
    )
    setup_embed.add_field(
        name="Runner Role", value=f"<@&{setup_view.role}>", inline=True
    )
    setup_embed.add_field(
        name="Connect Channel", value=f"<#{channel_view.connect}>", inline=True
    )
    setup_embed.add_field(
        name="RCON Channel", value=f"<#{channel_view.rcon}>", inline=True
    )
    await interaction.edit_original_message(content=None, embed=setup_embed, view=None)
    database.add_new_guild(
        interaction.guild_id, setup_view.role, channel_view.connect, channel_view.rcon
    )
    print("New Server: " + str(interaction.guild_id))


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
    database.set_guild_serveme(interaction.guild_id, api_key)
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

    if team.currentplayers:
        embed_color = 0xCCCCDC
    else:
        embed_color = 0xFEF0C7

    url = "https://rgl.gg/Public/Team.aspx?t=" + str(team.teamid)

    embed = nextcord.Embed(title=team.name, url=url, color=embed_color)

    embed.add_field(name=team.tag, value="", inline=True)
    if team.rank:
        embed.add_field(name="Team Rank", value=team.rank, inline=True)

    embed.add_field(name=team.seasonname, value=team.division, inline=False)

    player_text = ""
    for player in team.currentplayers:
        player_text += "["
        if player["isLeader"]:
            player_text += ":star: "
        player_text += (
            player["name"]
            + f"""](https://rgl.gg/Public/PlayerProfile.aspx?p={player["steamId"]})\n"""
        )
    if player_text:
        embed.add_field(name="Current Players", value=player_text, inline=False)

    player_text = ""
    for player in team.formerplayers:
        player_text += "["
        if player["isLeader"]:
            player_text += ":star: "
        player_text += (
            player["name"]
            + f"""](https://rgl.gg/Public/PlayerProfile.aspx?p={player["steamId"]})\n"""
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

    if "https://rgl.gg/Public/PlayerProfile.aspx?" in message.content:
        regex = re.search(
            r"(?<=https:\/\/rgl\.gg\/Public\/PlayerProfile\.aspx\?p=)[0-9]*",
            message.content,
        )
        if regex is None:
            return
        player = await RGL.create_player(int(get_steam64(regex.group(0))))
        embed = await create_player_embed(player)
        await message.channel.send(embed=embed)
    elif "https://rgl.gg/Public/Team.aspx?" in message.content:
        regex = re.search(
            r"(?<=https:\/\/rgl\.gg\/Public\/Team\.aspx\?t=)[0-9]*",
            message.content,
        )
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
        steamid (str): The player to search for.
    """
    await interaction.response.defer()
    if discord_user is not None:
        steam_id = database.get_steam_from_discord(discord_user.id)
        print(steam_id)
        rgl = await RGL.create_player(int(get_steam64(steam_id)))
    elif steamid is not None:
        rgl = await RGL.create_player(int(get_steam64(steamid)))
    else:
        await interaction.send("You must specify a user or steam ID.", ephemeral=True)
        return
    embed = await create_player_embed(rgl)
    await interaction.send(embed=embed)


@bot.slash_command(guild_ids=TESTING_GUILDS)
async def test(_interaction: nextcord.Interaction):
    """
    This is the main slash command that will be the prefix of all commands below.
    This will never get called since it has subcommands.
    """


class BranchSelect(nextcord.ui.View):
    """Opens a string select dropdown to select the branch to switch the bot to."""

    def __init__(self, branches: list[str]):
        super().__init__()
        self.branches: list[nextcord.SelectOption] = []
        for branch in branches:
            self.branches.append(nextcord.SelectOption(label=branch))
        self.select = nextcord.ui.StringSelect(
            placeholder="Select a branch", options=self.branches, row=1
        )
        self.add_item(self.select)

    @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green, row=2)
    async def finish(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Continues setup"""
        self.stop()


@test.subcommand(
    name="branch", description="Switch the branch that the test bot is deployed under."
)
async def switch_branch(interaction: nextcord.Interaction):
    """Switches the branch that the test bot account is currently deployed off of."""
    await interaction.response.defer()
    if interaction.user.get_role(1144720671558078485) is None:
        await interaction.send(
            "You do not have the Contributors role and cannot run this command.",
            ephemeral=True,
        )
        return

    github_api = AIOHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"bearer {GITHUB_API_KEY}"},
    )

    branch_names = []
    async with Client(
        transport=github_api,
        fetch_schema_from_transport=False,
    ) as session:
        list_branches = gql(
            """
            query getBranches {
                repository(name: "pugBot", owner: "Ooglely") {
                    refs(first: 25, refPrefix: "refs/heads/") {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
            """
        )

        result = await session.execute(list_branches)
        for branch in result["repository"]["refs"]["edges"]:
            branch_names.append(branch["node"]["name"])
    branch_select = BranchSelect(branch_names)
    await interaction.send(
        "Select a branch to deploy.", view=branch_select, ephemeral=False
    )
    status = await branch_select.wait()
    if not status:
        selected_branch = branch_select.select.values[0]
        railway_api = AIOHTTPTransport(
            url="https://backboard.railway.app/graphql/v2",
            headers={"Authorization": f"Bearer {RAILWAY_API_KEY}"},
        )

        async with Client(
            transport=railway_api,
            fetch_schema_from_transport=False,
        ) as session:
            set_deployment_trigger = gql(
                f"""
                mutation setDeploymentTrigger {{
                    deploymentTriggerUpdate(
                        id: "275e3203-4ac7-4ada-84de-1c11f8b9b124",
                        input: {{
                            branch: "{selected_branch}",
                            checkSuites: true,
                            repository: "Ooglely/pugBot",
                        }}
                    ) {{
                        id
                    }}
                }}
                """
            )

            redeploy_environment = gql(
                """
                mutation deployNewDeployment {
                    environmentTriggersDeploy(
                        input: {
                            environmentId: "5c2a716b-7bac-4dae-9ee4-78725cb1ee1a",
                            projectId: "8ffd3860-8187-406a-bf03-69d7356ec462",
                            serviceId: "01b0b783-64b1-4727-b8c9-5df09701c8ac"
                        }
                    )
                }
                """
            )

            await session.execute(set_deployment_trigger)
            await session.execute(redeploy_environment)
        await interaction.edit_original_message(
            content=f"Switching branch to `{selected_branch}`... Please check <#1144720434370203698> to see deployment progress.",
            view=None,
        )


@bot.slash_command(
    name="help", description="Displays all the bots commands and their purpose."
)
async def help(interaction: nextcord.Interaction):  # pylint: disable=redefined-builtin
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
        value="/setup - Used to setup the bot for a guild (Admin only)\n/serveme - Used to set the serveme api key for a guild (Admin only)\n/registration - Sets up tf.oog.pw registration (Admin only)\n/register - Registers a player in the bot's database\n/search - Search for a player's RGL profile\n/reserve - Get a new reservation from na.serveme.tf\n/map - Change the map on a running reservation\n/rcon - Run an rcon command on an active reservation",
        inline=False,
    )
    if interaction.guild_id == 952817189893865482:
        help_embed.add_field(
            name="AGG Commands",
            value="/stats - Show a player's pug stats\n/move - Move all players after a pug is over\n/pug - Not implemented yet",
            inline=False,
        )
    help_embed.set_footer(text=VERSION)
    await interaction.send(embed=help_embed)


@tasks.loop(minutes=1)
async def update_status():
    """Updates the bot's status with various data."""
    statuses = [
        f"{len(bot.guilds)} guilds",
        "tf.oog.pw :3",
        f"{len(bot.users)} users",
        "sea otters :D",
        f"{database.player_count()} registered players",
        "meds drop :(",
    ]
    await bot.change_presence(
        activity=nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name=random.choice(statuses),
        )
    )


bot.run(DISCORD_TOKEN)
