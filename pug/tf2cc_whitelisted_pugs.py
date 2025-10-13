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
        self.tf2cc_serveme_key = asyncio.run(database.get_server(TF2CC_GUILD))["serveme"]

    @nextcord.slash_command()  # pylint: disable=no-member
    async def whitelist(self, interaction: nextcord.Interaction):
        """Never gets called, just a placeholder for the subcommand."""

    async def get_category_by_channel_id(self, channel_id: int):
        """Search for a pug catergory in TF2CC associated with the channel_id and return all known info

        Args: 
            channel_id (int): channel_id to search for

        Returns:
            dict: all information related to TF2CC the found pug category
        """
        query = [
            {
                "$match": {
                    "_id": TF2CC_GUILD
                }
            },
            {
                "$project": {
                    "categoriesArray": {
                        "$map": {
                            "input": {"$objectToArray": "$categories"},
                            "as": "category",
                            "in": {
                                "parentKey": "$$category.k",
                                "children": "$$category.v"
                            }
                        }
                    }
                }
            },
            {
                "$project": {
                    "categoriesArray": {
                        "$filter": {
                        "input": "$categoriesArray",
                        "cond": {"$eq": ["$$this.children.add_up", channel_id]}
                        }
                    }
                }
            },
            {
                "$unwind": "$categoriesArray"
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "parentKey": "$categoriesArray.parentKey",
                        "children": "$categoriesArray.children"
                    }
                }
            }
        ]

        try:
            result = await category_db.aggregate()
        except LookupError as exc:
            return None
        
        return result[0]


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

        before_channel: Optional[Union[VoiceChannel, StageChannel]] = before.channel.id
        after_channel: Optional[Union[VoiceChannel, StageChannel]] = after.channel.id

        before_category: Optional[list] = await self.get_category_by_channel_id(before_channel)
        after_category: Optional[list] = await self.get_category_by_channel_id(after_channel)

        if before_category is None and after_category is None or before_category["parentKey"] == after_category["parentKey"]:
            return

        if after_category is not None:
            after_reservations = get_servers_by_guild_and_category(TF2CC_GUILD, after_category["parentKey"])
            for res in after_reservations:
                res.add_to_whitelist(self.tf2cc_serveme_key, member)

        if before_category is not None:
            before_reservations = get_servers_by_guild_and_category(TF2CC_GUILD, before_category["parentKey"])
            for res in before_reservations:
                res.remove_from_whitelist(self.tf2cc_serveme_key, member)

