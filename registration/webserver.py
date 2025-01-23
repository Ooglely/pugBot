"""File holding the actual FastAPI webserver for use with the registration cog."""
import logging

from fastapi import FastAPI, APIRouter, Request, Response, status
from pydantic import BaseModel  # pylint: disable=no-name-in-module

from database import player_count, log_count
from constants import API_PASSWORD
from registration.registration import RegistrationCog


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


class Webserver:
    """Class setting up FastAPI routes and providing a cog for bot interaction"""

    def __init__(self, cog: RegistrationCog):
        self.app: FastAPI = FastAPI()
        self.cog: RegistrationCog = cog
        self.router: APIRouter = APIRouter()
        self.router.add_api_route(
            "/api/register",
            self.register,
            status_code=status.HTTP_201_CREATED,
            methods=["POST"],
        )
        self.router.add_api_route("/api/stats", self.get_bot_stats)
        self.app.include_router(self.router)

    async def register(
        self, registration: NewUser, request: Request, response: Response
    ):
        """Starts the registration process for a new user.

        Args:
            registration (NewUser): The steam and discord ID of the user
            request (Request): The request to check for the API password in the header

        Returns:
            dict: Describes success or errors
        """
        logging.info(registration)
        if "password" in request.headers:
            if request.headers["password"] == API_PASSWORD:
                result = await self.cog.register_new_user(
                    int(registration.discord), int(registration.steam)
                )

                # result will be None on success, string if an error occurred
                if result:
                    response.status_code = status.HTTP_409_CONFLICT
                    return {"error": f"Unable to register user: {result}"}

                return {"message": "Success"}
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"error": "Wrong API password. Contact pugBot devs."}
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Wrong API password. Contact pugBot devs."}

    async def get_bot_stats(self, response: Response):
        """Returns the number of players in the database."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        stats = {"players": await player_count(), "logs": await log_count()}
        return stats
