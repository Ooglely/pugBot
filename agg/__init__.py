"""This file contains the classes used in the agg commands,
and the IDs for the agg guild and channels."""
from pydantic import BaseModel  # pylint: disable=no-name-in-module


class NewUser(BaseModel):
    """Pydantic model for a new user from the website

    Attributes:
        steam (str): The user's steam ID
        discord (str): The user's discord ID
    """

    steam: str
    discord: str


class NewConnect(BaseModel):
    """Pydantic model for a new connect command from the TF2 server

    Attributes:
        discordID (str): The discord ID to send the connect command to
        connectCommand (str): The connect command to send to the user
    """

    discordID: str
    connectCommand: str


class PugCategory:
    """Class to hold the channel IDs for the HL and AD pug categories

    Attributes:
        organizing (int): The organizing voice channel ID
        inp (int): The inp voice channel ID
        teams (list[int]): The team voice channel IDs
    """

    def __init__(self, organizing: int, inp: int, teams: list[int]):
        self.organizing: int = organizing
        self.inp: int = inp
        self.teams: list[int] = teams


AGG_SERVER_ID = [952817189893865482, 1110667963163476032]
HL_CHANNELS: PugCategory = PugCategory(
    996567486621306880, 1009978053528670371, [987171351720771644, 994443542707580951]
)
AD_CHANNELS: PugCategory = PugCategory(
    997602270592118854, 1077390612644515861, [997602308525404242, 997602346173464587]
)
