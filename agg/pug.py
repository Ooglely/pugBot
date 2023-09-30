"""A cog that holds all of the commands to run pugs in agg."""
import nextcord
from nextcord.ext import commands
from agg import HL_CHANNELS, AD_CHANNELS
from servers.serveme_api import ServemeAPI

serveme: ServemeAPI = ServemeAPI()


class PugCog(commands.Cog):
    """A cog that holds all the commands for pug running in agg.

    Attributes:
        bot (nextcord.Client): The bot client.
        organizing (bool): Whether or not a pug is being organized.
        last_log (int): Last log sent in the log channel.
    """

    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.organizing: bool = False
        self.last_log: int = 0

    @commands.Cog.listener(name="on_voice_state_update")
    async def first_to_18(self, _member, state_before, _state_after):
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
            if state_before.channel is None:
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
