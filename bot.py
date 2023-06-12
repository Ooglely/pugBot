"""Main file for running and starting the bot, with general global commands."""
import nextcord
from nextcord.ext import commands

import database
from rgl_api import RGL_API, Player
from constants import BOT_COLOR, NEW_COMMIT_NAME, VERSION, DISCORD_TOKEN
from util import get_steam64
from servers.servers import ServerCog
from agg.webserver import WebserverCog
from agg.stats import StatsCog
from agg.pug import PugCog
from agg.update_roles import UpdateRolesCog

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
bot.remove_command("help")

RGL: RGL_API = RGL_API()


@bot.event
async def on_ready():
    """Prints bot information on ready, starts webserver, and syncs commands."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Running: {NEW_COMMIT_NAME}")
    print("------")
    # Need to add cog on ready instead of before for webserver async to be friendly
    bot.add_cog(WebserverCog(bot))


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


@bot.listen("on_message")
async def player_listener(message: nextcord.Message):
    """Listener for messages that contain a link to a player's rgl profile.

    Args:
        message (nextcord.Message): The message to check.
    """
    if message.content.startswith("https://rgl.gg/Public/PlayerProfile.aspx?"):
        rgl = await RGL.create_player(int(get_steam64(message.content)))
        embed = await create_player_embed(rgl)
        await message.channel.send(embed=embed)


@bot.slash_command(
    name="search", description="Search for an RGL profile and display it."
)
async def search(interaction: nextcord.Interaction, steamid: str):
    """Search for a players RGL profile and generate the embed.

    Args:
        interaction (nextcord.Interaction): The interaction to respond to.
        steamid (str): The player to search for.
    """
    rgl = await RGL.create_player(int(get_steam64(steamid)))
    embed = await create_player_embed(rgl)
    await interaction.send(embed=embed)


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
        value="""/setup - Used to setup the bot for a guild (Admin only)
                 /serveme - Used to set the serveme api key for a guild(Admin only)
                 /search - Search for a player's RGL profile
                 /reserve - Get a new reservation from na.serveme.tf
                 /map - Change the map on a running reservation
                 /rcon - Run an rcon command on an active reservation""",
        inline=False,
    )
    if interaction.guild_id == 952817189893865482:
        help_embed.add_field(
            name="AGG Commands",
            value="""/stats - Show a player's pug stats
                     /register - Register a new user in the database
                     /move - Move all players after a pug is over
                     /pug - Not implemented yet""",
            inline=False,
        )
    help_embed.set_footer(text=VERSION)
    await interaction.send(embed=help_embed)


bot.run(DISCORD_TOKEN)
