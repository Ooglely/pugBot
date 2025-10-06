"""Cog that handles stats and showing stats to players."""

from typing import Optional
import nextcord
from nextcord.ext import commands

from constants import BOT_COLOR
from database import BotCollection
from logs.elo import get_elo, Elo
from logs.elo_cog import EloSettings, EloCog
from util import is_runner, get_steam64

player_db = BotCollection("players", "data")


class StatsCog(commands.Cog):
    """This cog contains the stats commands."""

    def __init__(self, bot):
        self.bot = bot

    @nextcord.slash_command(
        name="stats",
        description="Show your own stats and ELO rating.",
    )
    async def stats(self, interaction: nextcord.Interaction):
        """Show your own stats."""
        stats_embed = nextcord.Embed(
            title=f"{interaction.user.name}'s stats",
            description="Fetching stats...",
            color=BOT_COLOR,
        )
        stats_embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.send(embed=stats_embed)
        try:
            player = await player_db.find_item({"discord": str(interaction.user.id)})
        except LookupError:
            stats_embed.description = "Unable to find your stats."
            await interaction.edit_original_message(embed=stats_embed)
            return

        elo_ratings: Elo = await get_elo(int(player["steam"]))
        stats_embed.description = None
        stats_embed.add_field(
            name="Sixes ELO",
            value=f"{elo_ratings.global_elo.sixes}",
            inline=True,
        )
        stats_embed.add_field(
            name="Highlander ELO",
            value=f"{elo_ratings.global_elo.highlander}",
            inline=True,
        )
        stats_embed.add_field(
            name="Passtime ELO",
            value=f"{elo_ratings.global_elo.passtime}",
            inline=True,
        )

        elo_settings: EloSettings = EloSettings(interaction.guild.id)
        await elo_settings.load()
        server_elo: str | int
        if elo_settings.visible is True:
            server_elo = await elo_ratings.get_elo_from_mode(
                "server", interaction.guild.id
            )
        else:
            server_elo = "*hidden*"

        stats_embed.add_field(
            name="Server ELO",
            value=server_elo,
            inline=False,
        )

        stats_embed.set_footer(text="See more detailed stats at pugbot.tf (soon)")
        await interaction.edit_original_message(embed=stats_embed)

    @is_runner()
    @EloCog.elo.subcommand(name="search")  # pylint: disable=no-member
    async def stats_search(
        self,
        interaction: nextcord.Interaction,
        discord: Optional[nextcord.User] = nextcord.SlashOption(
            name="discord", description="The user to look up.", required=False
        ),
        steam: Optional[str] = nextcord.SlashOption(
            name="steam", description="The steam ID to look up.", required=False
        ),
    ):
        """Search for a player's stats."""
        user: nextcord.User
        steam_id: str
        if discord is None and steam is None:
            await interaction.send(
                "You must provide either a discord or steam ID to search for."
            )
            return
        if discord is not None:
            user = discord
            try:
                player = await player_db.find_item({"discord": str(discord.id)})
            except LookupError:
                await interaction.send("Unable to find provided user.")
                return
            steam_id = player["steam"]
        elif steam is not None:
            steam_id = steam
            try:
                player = await player_db.find_item({"steam": str(get_steam64(steam))})
            except LookupError:
                await interaction.send("Unable to find provided user.")
                return
            user = await self.bot.fetch_user(int(player["discord"]))

        stats_embed = nextcord.Embed(
            title=f"{user.name}'s stats",
            description="Fetching stats...",
            color=BOT_COLOR,
        )
        stats_embed.set_thumbnail(url=user.avatar.url)
        await interaction.send(embed=stats_embed)

        elo_ratings: Elo = await get_elo(steam=int(steam_id))
        print(elo_ratings.as_dict())
        stats_embed.description = None
        stats_embed.add_field(
            name="Sixes ELO",
            value=f"{elo_ratings.global_elo.sixes}",
            inline=True,
        )
        stats_embed.add_field(
            name="Highlander ELO",
            value=f"{elo_ratings.global_elo.highlander}",
            inline=True,
        )
        stats_embed.add_field(
            name="Passtime ELO",
            value=f"{elo_ratings.global_elo.passtime}",
            inline=True,
        )

        server_elo = await elo_ratings.get_elo_from_mode("server", interaction.guild.id)
        stats_embed.add_field(
            name="Server ELO",
            value=server_elo,
            inline=False,
        )

        try:
            category_string = ""
            for category, elo in elo_ratings.server_elo[
                str(interaction.guild.id)
            ].categories.items():
                print(category)
                print(elo)
                category_string += f"{category}: {elo}\n"

            if len(category_string) != 0:
                stats_embed.add_field(
                    name="Server ELO by category",
                    value=category_string,
                    inline=False,
                )
        except ValueError:
            pass

        stats_embed.url = f"https://logs.tf/profile/{steam_id}"
        stats_embed.set_footer(
            text="See more detailed stats at pugbot.tf (soon) | Steam ID: " + steam_id
        )
        await interaction.edit_original_message(embed=stats_embed)
