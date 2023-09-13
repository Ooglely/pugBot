"""Implements the log searcher file, which takes the players from a team generation or moved back and searches for the log associated with the game that was played/being played."""
from util import get_steam64
import time
from pug import PugCategory
class Player():
    def __init__(self, steam: int | None, discord: int | None) -> None:
        self.steam: int | None = int(get_steam64(str(steam))) if steam is not None else None
        self.discord: int | None = discord if discord is not None else None


class PartialLog():
    def __init__(self, category: PugCategory) -> None:
        self.timestamp: int = time.time().__round__()
        self.category: PugCategory
        self.players: list[] =

if __name__ == "__main__":

