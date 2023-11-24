"""This cog contains the elo cog with commands to configure elo and add missing logs."""
import time

from bson import Int64 as NumberLong
import nextcord
from nextcord.ext import commands

from database import BotCollection
from registration import TrueFalseSelect
from constants import BOT_COLOR
from logs import Player
from logs.searcher import FullLog, PartialLog
from logs.logstf_api import LogsAPI
from logs.elo import process_elo
from pug import PugCategory, CategoryButton, CategorySelect
from util import is_runner, get_steam64

config_db: BotCollection = BotCollection("guilds", "config")
logs_db: BotCollection = BotCollection("logs", "list")
category_db: BotCollection = BotCollection("guilds", "categories")


class EloSettings:
    """Stores elo settings for a guild."""

    def __init__(self, guild_id: int):
        self.guild_id: int = guild_id
        self.enabled: bool = False
        self.mode: str = "global"
        self.visible: bool = False

    async def load(self):
        """Load elo settings from the database."""
        try:
            guild_settings = await config_db.find_item(
                {"guild": NumberLong(str(self.guild_id))}
            )
            print(guild_settings)
            if "elo" in guild_settings:
                log_settings = guild_settings["elo"]
            else:
                log_settings = {
                    "enabled": False,
                    "mode": "global",
                    "visible": False,
                }
        except LookupError:
            log_settings = {
                "enabled": False,
                "mode": "global",
                "visible": False,
            }
        self.enabled = log_settings["enabled"]
        self.mode = log_settings["mode"]
        self.visible = log_settings["visible"]

    async def save(self):
        """Save elo settings to the database."""
        log_settings = {
            "enabled": self.enabled,
            "mode": self.mode,
            "visible": self.visible,
        }
        await config_db.update_item(
            {"guild": self.guild_id}, {"$set": {"elo": log_settings}}
        )


class EloModeSelect(nextcord.ui.View):
    """View to select the elo mode."""

    def __init__(self):
        super().__init__()
        self.mode: str = "gamemode"

    @nextcord.ui.button(label="Global", style=nextcord.ButtonStyle.grey)
    async def global_mode(
        self, _button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        """Select global elo mode."""
        self.mode = "gamemode"
        await interaction.response.edit_message(view=None)
        self.stop()

    @nextcord.ui.button(label="Server", style=nextcord.ButtonStyle.grey)
    async def server_mode(
        self, _button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        """Select server elo mode."""
        self.mode = "server"
        await interaction.response.edit_message(view=None)
        self.stop()

    @nextcord.ui.button(label="Category", style=nextcord.ButtonStyle.grey)
    async def category_mode(
        self, _button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        """Select category elo mode."""
        self.mode = "category"
        await interaction.response.edit_message(view=None)
        self.stop()


class EloCog(commands.Cog):
    """This cog contains the logs command and its subcommands."""

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(name="elo", description="Set up the ELO system for this server.", default_member_permissions=nextcord.Permissions(manage_guild=True))
    async def elo(self, _interaction: nextcord.Interaction):
        """Main elo command group"""

    @elo.subcommand(name="setup")
    async def elo_setup(self, interaction: nextcord.Interaction):
        """Setup the elo settings for a guild."""
        setup_embed = nextcord.Embed(
            title="Elo Setup",
            color=BOT_COLOR,
        )

        elo_settings = EloSettings(interaction.guild.id)
        await elo_settings.load()
        print(elo_settings.__dict__)

        setup_embed.description = "Would you like to enable elo?\nPlease note that only players registered with the bot through pugbot.tf will be tracked in the elo system."
        elo_enable = TrueFalseSelect()
        await interaction.send(embed=setup_embed, view=elo_enable)
        setup_status = await elo_enable.wait()
        if setup_status:
            await interaction.delete_original_message(delay=1)
            return
        if not elo_enable.selection:
            elo_settings.enabled = False
            await elo_settings.save()
            setup_embed.description = "Elo has been disabled."
            await interaction.edit_original_message(embed=setup_embed, view=None)
            await interaction.delete_original_message(delay=30)
            return
        await interaction.edit_original_message(view=None)
        elo_settings.enabled = True

        setup_embed.description = "What type of elo would you like to use?"
        setup_embed.add_field(
            name="Global/Gamemode",
            value="Global elo is shared across all servers and is specific to each gamemode (6s, HL, Passtime).",
        )
        setup_embed.add_field(
            name="Server", value="Server elo is specific to each server."
        )
        setup_embed.add_field(
            name="Category",
            value="Category elo is specific to each category within the server.",
        )
        mode_select = EloModeSelect()
        await interaction.edit_original_message(embed=setup_embed, view=mode_select)
        await mode_select.wait()
        elo_settings.mode = mode_select.mode
        await interaction.edit_original_message(view=None)

        setup_embed.clear_fields()
        setup_embed.description = (
            "Would you like to make the server elo visible to all users?"
        )
        visible_select = TrueFalseSelect()
        await interaction.edit_original_message(embed=setup_embed, view=visible_select)
        await visible_select.wait()
        elo_settings.visible = visible_select.selection

        await elo_settings.save()
        setup_embed.description = f"Elo has been setup.\nEnabled: {elo_settings.enabled}\nMode: {elo_settings.mode}\nVisible: {elo_settings.visible}"
        setup_embed.add_field(
            name="Reminder",
            value="Players must be registered with the bot to be tracked in the elo system.",
        )
        await interaction.edit_original_message(embed=setup_embed, view=None)
        await interaction.delete_original_message(delay=60)

    @is_runner()
    @elo.subcommand(name="update")
    async def add_log(self, interaction: nextcord.Interaction, logstf_id: int):
        """Update the elo of all players in a log."""
        try:
            # If the log already exists we don't wanna add it again.
            result = await logs_db.find_item({"log_id": int(logstf_id)})
            await interaction.send(
                content=f"Log #{result['log_id']} already exists in the database."
            )
            return
        except LookupError:
            await interaction.send(content="Looking for log...")
            players: list[Player] = []
            log = await LogsAPI.get_single_log(logstf_id)
            for player in log["players"]:
                print(player)
                log_player = Player(steam=get_steam64(player))
                await log_player.link_player()
                players.append(log_player)

            # Need the category that the log was played in
            try:
                result = await category_db.find_item({"_id": interaction.guild.id})
                categories = result["categories"]
            except LookupError:
                await interaction.send(
                    "There are no pug categories setup for this server.\nPlease run /pug category add to add a pug category."
                )
                return
            select_view = CategorySelect()

            for name, _category in categories.items():
                disabled: bool = False
                color = nextcord.ButtonStyle.gray
                button = CategoryButton(name=name, color=color, disabled=disabled)
                select_view.add_item(button)

            pug_embed = nextcord.Embed(
                title="Generate Teams",
                color=BOT_COLOR,
                description="Select the category this log was played in.",
            )
            await interaction.edit_original_message(embed=pug_embed, view=select_view)
            embed_status = await select_view.wait()
            if embed_status or select_view.name == "cancel":
                return

            chosen_category: PugCategory = PugCategory(
                select_view.name, categories[select_view.name]
            )

            full_log = FullLog(
                PartialLog(
                    interaction.guild.id,
                    chosen_category,
                    players,
                    round(time.time()),
                ),
                logstf_id,
                log,
            )

            await logs_db.add_item(full_log.export())
            await process_elo(full_log)
            await interaction.edit_original_message(
                content="Elo has been updated.", embed=None, view=None
            )

    @commands.is_owner()
    @elo.subcommand(name="fullupdate")
    async def full_elo_update(self, interaction: nextcord.Interaction):
        """Update the elo of all players using the full backlog of logs."""
        await interaction.send(content="Updating elo...")
        all_logs = await logs_db.find_all_items()
        for log in all_logs:
            print(log)
            players = [Player(data=player) for player in log["players"]]
            full_log = FullLog(
                PartialLog(
                    log["guild"],
                    PugCategory(log["category"]["name"], log["category"]),
                    players,
                    log["timestamp"],
                ),
                log["log_id"],
                await LogsAPI.get_single_log(log["log_id"]),
            )
            await process_elo(full_log)
