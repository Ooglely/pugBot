import os
import discord
from discord.ext import commands, tasks
from discord import app_commands


class PugCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pug_running = False
        self.organizing = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, state_before, state_after):
        agg_server = self.bot.get_guild(952817189893865482)
        hl_organizing = agg_server.get_channel(996567486621306880)
        sixes_organizing = agg_server.get_channel(997602270592118854)
        hl_inp = agg_server.get_channel(1009978053528670371)
        sixes_inp = agg_server.get_channel(1077390612644515861)
        log_channel = agg_server.get_channel(1026985050677465148)

        if self.organizing != True:
            if len(hl_organizing.members) >= 18:
                # Highlander pug is forming
                # In the future after I have assured this works I will change it to move to inp channel
                player_string = ""
                for player in hl_organizing.members:
                    await player.move_to(hl_inp)
                    player_string += f"{player.mention} "

                await log_channel.send(
                    f"First 18 players in organizing: {player_string}"
                )
                self.organizing = True

            elif len(sixes_organizing.members) >= 18:
                player_string = ""
                for player in sixes_organizing.members:
                    await player.move_to(sixes_inp)
                    player_string += f"{player.mention} "

                await log_channel.send(
                    f"First 18 players in organizing: {player_string}"
                )
                self.organizing = True
        else:
            players = []
            for channel in agg_server.voice_channels:
                for member in channel.members:
                    players.append(member.id)

            if len(players) < 5:
                await log_channel.send(
                    f"Assuming that pugs are dead. Resetting first to 18 tracker."
                )
                self.organizing = False


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PugCog(bot))
