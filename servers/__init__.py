import nextcord


class Servers(nextcord.ui.View):
    def __init__(self):
        super().__init__()
        self.server_chosen = None


class ServerButton(nextcord.ui.Button):
    def __init__(self, reservation, num):
        self.num = num
        super().__init__(
            label=f"ID #{reservation['id']} - {reservation['server']['name']}",
            custom_id=str(num),
            style=nextcord.ButtonStyle.blurple,
        )

    async def callback(self, interaction: nextcord.Interaction):
        super().view.server_chosen = self.num
        super().view.stop()
