"""Classes for use in the servers cog."""
import nextcord
import aiohttp


class Servers(nextcord.ui.View):
    """Displays the current servers and allows the user to select one."""

    def __init__(self):
        super().__init__()
        self.server_chosen = None


class ServerButton(nextcord.ui.Button):
    """A button representing a server."""

    def __init__(self, reservation, num):
        self.num = num
        super().__init__(
            label=f"ID #{reservation['id']} - {reservation['server']['name']}",
            custom_id=str(num),
            style=nextcord.ButtonStyle.blurple,
        )

    async def callback(
        self, interaction: nextcord.Interaction
    ):  # pylint: disable=unused-argument
        """Callback for when the button is pressed."""
        super().view.server_chosen = self.num
        super().view.stop()


class Reservation:
    """Represents a reservation on serveme.tf

    Attributes:
        id (int): The ID of the reservation
        api_key (str): The API key associated with the reservation
        message_ids (list[int]): The message IDs associated with the reservation
    """

    def __init__(self, id_num: int, api_key: str, messages) -> None:
        self.id_num = id_num
        self.api_key = api_key
        self.messages = messages

    async def is_active(self) -> bool:
        """Checks if the reservation is still active

        Returns:
            bool: True if the reservation is still active, False otherwise
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://na.serveme.tf/api/reservations/{self.id_num}?api_key={self.api_key}",
            ) as resp:
                server = await resp.json()
                print(server)
                if server["reservation"]["status"] == "Ended":
                    return False
                return True
