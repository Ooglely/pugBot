import nextcord
import database
from nextcord.ext import commands, tasks
import constants

intents = nextcord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

activity = nextcord.Activity(name="tf.oog.pw :3", type=nextcord.ActivityType.watching)
bot = commands.Bot(command_prefix="x!", intents=intents, activity=activity)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Running Rewrite: {constants.NEW_COMMIT_NAME}")
    print("------")


class SetupView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.role = None

    @nextcord.ui.role_select(placeholder="Select a role", row=1)
    async def role(
        self, role: nextcord.ui.RoleSelect, interaction: nextcord.Interaction
    ):
        await interaction.response.defer()
        self.role = role.values[0].id
        self.stop()


class ChannelView(nextcord.ui.View):
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
        await interaction.response.defer()
        self.connect = channel.values[0].id
        if self.rcon is not None:
            self.stop()

    @nextcord.ui.channel_select(placeholder="Select a rcon channel")
    async def rcon(
        self, channel: nextcord.ui.ChannelSelect, interaction: nextcord.Interaction
    ):
        await interaction.response.defer()
        self.rcon = channel.values[0].id
        if self.connect is not None:
            self.stop()


class ApiInput(nextcord.ui.TextInput):
    def __init__(self):
        super().__init__(
            label="Serveme API Key", placeholder="Enter your Serveme API Key", row=1
        )

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer()
        self.view.serveme = self.value
        self.view.stop()


class ApiView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.serveme = None
        self.add_item(ApiInput())


@bot.slash_command(guild_ids=constants.TESTING_GUILDS)
async def setup(interaction: nextcord.Interaction):
    setup_view = SetupView()
    channel_view = ChannelView()
    api_view = ApiView()
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
    database.new_server(
        interaction.guild_id,
        setup_view.role,
        channel_view.connect,
        channel_view.rcon,
        api_view.serveme,
    )


@bot.slash_command(guild_ids=constants.TESTING_GUILDS)
async def setup_test(interaction: nextcord.Interaction):
    settings = database.get_server(interaction.guild_id)
    print(settings)
    await interaction.send("test")


@bot.slash_command(guild_ids=constants.TESTING_GUILDS)
async def serveme(interaction: nextcord.Interaction, api_key: str):
    database.set_guild_serveme(interaction.guild_id, api_key)
    await interaction.send("Serveme API Key set!")


bot.run(constants.DISCORD_TOKEN)
