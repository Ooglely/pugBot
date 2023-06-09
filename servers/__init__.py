"""Classes for use in the servers cog."""
import nextcord


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
