import nextcord, nextcord.ext.commands as commands, nextcord.ext.tasks as tasks
from constants import TESTING_GUILDS
from agg import AGG_SERVER_ID


class PugCog(commands.Cog):
    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot
        self.organizing: bool = False

    @commands.Cog.listener(name="on_voice_state_update")
    async def first_to_18(self, member, state_before, state_after):
        agg_server: nextcord.Guild = self.bot.get_guild(952817189893865482)
        log_channel: nextcord.VoiceChannel = agg_server.get_channel(1026985050677465148)

        hl_organizing: nextcord.VoiceChannel = agg_server.get_channel(
            996567486621306880
        )
        hl_inp: nextcord.VoiceChannel = agg_server.get_channel(1009978053528670371)

        ad_organizing: nextcord.VoiceChannel = agg_server.get_channel(
            997602270592118854
        )
        ad_inp: nextcord.VoiceChannel = agg_server.get_channel(1077390612644515861)

        if self.organizing:
            # Just an extra check to make sure repeat moves aren't done
            if state_before.channel == None and state_after.channel == hl_organizing:
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
                for member in channel.members:
                    players.append(member.id)

            if len(players) <= 0:
                await log_channel.send(
                    "Assuming that pugs are dead. Resetting first to 18 tracker."
                )
                self.organizing = True

    async def move(self):
        agg_server: nextcord.Guild = self.bot.get_guild(952817189893865482)

        hl_organizing: nextcord.VoiceChannel = agg_server.get_channel(
            996567486621306880
        )
        hl_inp: nextcord.VoiceChannel = agg_server.get_channel(1009978053528670371)

    async def pug(self):
        pass

    async def logs(self):
        pass
