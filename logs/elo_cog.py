"""This cog contains the elo cog with commands to configure elo and add missing logs."""
import asyncio
import time

from bson import Int64 as NumberLong
import nextcord
from nextcord.ext import commands, application_checks

from database import BotCollection
from constants import BOT_COLOR
from logs import Player
from logs.searcher import FullLog, PartialLog
from logs.logstf_api import LogsAPI
from logs.elo import process_elo
from menus import BotMenu
from menus.callbacks import action_callback
from menus.templates import send_boolean_menu
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


class EloCog(commands.Cog):
    """This cog contains the logs command and its subcommands."""

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @nextcord.slash_command(name="elo")
    async def elo(self, _interaction: nextcord.Interaction):
        """Main elo command group"""

    @application_checks.has_permissions(manage_guild=True)
    @elo.subcommand(
        name="setup",
        description="Set up the ELO system for this server.",
    )
    async def elo_setup(self, interaction: nextcord.Interaction):
        """Setup the elo settings for a guild."""
        if interaction.guild is None:
            return

        setup_embed: nextcord.Embed = nextcord.Embed(
            title="Elo Setup",
            color=BOT_COLOR,
        )

        elo_settings = EloSettings(interaction.guild.id)
        await elo_settings.load()
        menu: BotMenu = BotMenu(embed=setup_embed, user_id=interaction.user.id)
        if menu.embed is None:
            return

        menu.embed.description = "Would you like to enable elo?\nPlease note that only players registered with the bot through pugbot.tf will be tracked in the elo system."
        try:
            result: bool = await send_boolean_menu(menu, interaction)
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return
        if result == "disable":
            elo_settings.enabled = False
            await elo_settings.save()
            setup_embed.description = "Elo has been disabled."
            await interaction.edit_original_message(embed=setup_embed, view=None)
            await interaction.delete_original_message(delay=30)
            return

        elo_settings.enabled = True

        menu.embed.description = "What type of elo would you like to use?"
        menu.embed.add_field(
            name="Global/Gamemode",
            value="Global elo is shared across all servers and is specific to each gamemode (6s, HL, Passtime).",
        )
        menu.embed.add_field(
            name="Server", value="Server elo is specific to each server."
        )
        menu.embed.add_field(
            name="Category",
            value="Category elo is specific to each category within the server.",
        )
        menu.clear_items()
        # Why did I not just name the entry global... not worth changes all db entries to fit new name
        menu.add_button(
            "Global",
            await action_callback("gamemode", interaction.user.id),
            nextcord.ButtonStyle.grey,
        )
        await menu.add_action_buttons(["server", "category"], interaction.user.id)
        await menu.edit(interaction)
        if not await menu.wait_for_action(self.bot) or menu.action is None:
            await interaction.delete_original_message(delay=1)
            return
        elo_settings.mode = menu.action

        menu.clear_items()
        menu.embed.clear_fields()
        menu.embed.description = (
            "Would you like to make the server elo visible to all users?"
        )
        try:
            result = await send_boolean_menu(menu, interaction)
        except TimeoutError:
            await interaction.delete_original_message(delay=1)
            return
        elo_settings.visible = result

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
            await asyncio.sleep(10)
