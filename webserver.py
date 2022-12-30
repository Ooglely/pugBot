import json
from discord.ext import commands, tasks
from fastapi import FastAPI, Request
import uvicorn
import asyncio
from pydantic import BaseModel

with open("config.json") as config_file:
    CONFIG = json.load(config_file)

API_PASSWORD = CONFIG["webserver"]["password"]

app = FastAPI()


class WebserverCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(start_server())


class NewUser(BaseModel):
    steam: str
    discord: str


async def start_server():
    config = uvicorn.Config("webserver:app", port=1496, log_level="info")
    server = uvicorn.Server(config)
    # server.serve()
    await server.serve()


@app.get("/")
async def hello_world():
    return {"message": "Hello world"}


@app.post("/api/register")
async def register(registration: NewUser, request: Request):
    if "password" in request.headers:
        if request.headers["password"] == API_PASSWORD:
            print(registration.steam)
            print(registration.discord)
            return {"message": "Hello world"}
        else:
            return {"message": "Wrong password"}
