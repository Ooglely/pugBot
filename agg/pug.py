"""
    A cog that holds all of the commands to run pugs in agg.
"""
import nextcord
from nextcord.ext import commands
from agg import AGG_SERVER_ID, PugCategory, HL_CHANNELS, AD_CHANNELS
from util import is_runner


class PugCog(commands.Cog):
    """A cog that holds all the commands for pug running in agg.

    Attributes:
        bot (nextcord.Client): The bot client.
        organizing (bool): Whether or not a pug is being organized.
    """

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.organizing: bool = False

    @commands.Cog.listener(name="on_voice_state_update")
    async def first_to_18(
        self, member, state_before, state_after
    ):  # pylint: disable=unused-argument
        """Moves the first 18 players in organizing to the inp channel.

        Keeps track of the first 18 players so that they are given priority to be chosen.

        Args:
            state_before (nextcord.VoiceState): The voice state before the update.
            state_after (nextcord.VoiceState): The voice state after the update.
        """
        agg_server: nextcord.Guild = self.bot.get_guild(952817189893865482)
        log_channel: nextcord.VoiceChannel = agg_server.get_channel(1026985050677465148)

        hl_organizing: nextcord.VoiceChannel = agg_server.get_channel(
            HL_CHANNELS.organizing
        )
        hl_inp: nextcord.VoiceChannel = agg_server.get_channel(HL_CHANNELS.inp)

        ad_organizing: nextcord.VoiceChannel = agg_server.get_channel(
            AD_CHANNELS.organizing
        )
        ad_inp: nextcord.VoiceChannel = agg_server.get_channel(AD_CHANNELS.inp)

        if self.organizing:
            # Just an extra check to make sure repeat moves aren't done
            if state_before.channel is None and state_after.channel == hl_organizing:
                # If enough players to start a HL pug...
                player_string: str = ""
                if len(hl_organizing.members) >= 18:
                    for player in hl_organizing.members:
                        await player.move_to(hl_inp)
                        player_string += f"{player.mention} "

                    await log_channel.send(
                        f"First 18 players in organizing: {player_string}"
                    )
                    self.organizing = False

                if len(ad_organizing.members) >= 18:
                    for player in ad_organizing.members:
                        await player.move_to(ad_inp)
                        player_string += f"{player.mention} "

                    await log_channel.send(
                        f"First 18 players in organizing: {player_string}"
                    )
                    self.organizing = False

        if not self.organizing:
            players = []
            for channel in agg_server.voice_channels:
                for user in channel.members:
                    players.append(user.id)

            if len(players) <= 0:
                await log_channel.send(
                    "Assuming that pugs are dead. Resetting first to 18 tracker."
                )
                self.organizing = True

    @nextcord.slash_command(name="move", guild_ids=AGG_SERVER_ID)
    @is_runner()
    async def move(self, interaction: nextcord.Interaction):
        """Moves all players after a pug is completed.

        Moves all players in the team channels to the organizing channel.
        Moves all players in the organizing channel to the in next pug channel.

        Args:
            interaction (nextcord.Interaction): The interaction that triggered the command.
        """
        await interaction.response.defer()

        agg_server: nextcord.Guild = self.bot.get_guild(952817189893865482)

        channels: PugCategory
        if interaction.channel.category.name == "HL Pugs":
            channels = HL_CHANNELS
        elif interaction.channel.category.name == "agg after dark":
            channels = AD_CHANNELS
        else:
            await interaction.send(
                "Please use this command in one of the pug channels."
            )
            return

        organizing: nextcord.VoiceChannel = agg_server.get_channel(channels.organizing)
        inp: nextcord.VoiceChannel = agg_server.get_channel(channels.inp)

        for player in organizing.members:
            await player.move_to(inp)

        for team_channel in channels.teams:
            team: nextcord.VoiceChannel = agg_server.get_channel(team_channel)
            for player in team.members:
                await player.move_to(organizing)

        await interaction.send("Moved players.")

    # async def pug(self):
    #    pass

    # async def logs(self):
    #    pass
