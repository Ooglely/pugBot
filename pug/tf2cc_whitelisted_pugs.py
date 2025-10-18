"""Commands and listeners for TF2CC's whitelisted pugs by heck."""
import asyncio
from typing import Optional, Set, Union

import nextcord
from nextcord import Member, StageChannel, VoiceChannel, VoiceState
from nextcord.ext import commands

from constants import TF2CC_GUILD
from database import BotCollection
import database
from pug import CategorySelect, CategoryButton, PugCategory, PugPlayer
from servers.servers import get_servers_by_guild_and_category


category_db = BotCollection("guilds", "categories")


class PugWhitelistedPugs(commands.Cog):
    """Cog storing all commands and listeners for TF2CC's whitelisted pugs"""

    def __init__(self, bot: nextcord.Client):
        self.bot = bot

    @nextcord.slash_command()  # pylint: disable=no-member
    async def whitelist(self, interaction: nextcord.Interaction):
        """Never gets called, just a placeholder for the subcommand."""

    def get_connect_channel(self, vc: VoiceChannel):
        """Search for a connect channel associated with the voice channel and return it's id
        Currently only works for TF2CC's categories

        Args: 
            vc (VoiceChannel): VoiceChannel to search for a associated connect channel for

        Returns:
            int: id of
        """
        category = vc.category

        connect_channel = None
        for channel in category.channels:
            if "connect" in channel.name:
                connect_channel = channel.id

        return connect_channel

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """Listen to all VoiceState updates and determine what to do in relation to pug whitelists

        Args:
            member (nextcord.Member): Member with VoiceState updates
            before (nextcord.Member): VoiceState info before change
            after (nextcord.Member): VoiceState info after change
        """

        if member.guild.id != TF2CC_GUILD:
            # Whitelisted pugs are not set up for other guilds ATM
            return

        self.tf2cc_serveme_key = (await database.get_server(TF2CC_GUILD))["serveme"]

        before_category: int = self.get_connect_channel(before.channel) if before.channel else None
        after_category: int = self.get_connect_channel(after.channel) if after.channel else None
        print(before_category, after_category)

        if before_category is None and after_category is None:
            return
        if before_category and after_category and before_category == after_category:
            return

        if after_category is not None:
            after_reservations = await get_servers_by_guild_and_category(TF2CC_GUILD, after_category)
            print(after_reservations)
            for res in after_reservations:
                await res.add_to_whitelist(self.tf2cc_serveme_key, member)

        if before_category is not None:
            before_reservations = await get_servers_by_guild_and_category(TF2CC_GUILD, before_category)
            print(before_reservations)
            for res in before_reservations:
                await res.remove_from_whitelist(self.tf2cc_serveme_key, member)

