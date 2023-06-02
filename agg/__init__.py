from pydantic import BaseModel
import nextcord


class NewUser(BaseModel):
    steam: str
    discord: str


class NewConnect(BaseModel):
    discordID: str
    connectCommand: str


AGG_SERVER_ID = [952817189893865482, 1110667963163476032]
