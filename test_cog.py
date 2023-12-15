import gql
import nextcord
from gql.transport.aiohttp import AIOHTTPTransport
from nextcord.ext import commands

from constants import (
    TESTING_GUILDS,
    GITHUB_API_KEY,
    RAILWAY_API_KEY,
    DEV_CONTRIBUTOR_ROLE,
)


class BranchSelect(nextcord.ui.View):
    """Opens a string select dropdown to select the branch to switch the bot to."""

    def __init__(self, branches: list[str]):
        super().__init__()
        self.branches: list[nextcord.SelectOption] = []
        for branch in branches:
            self.branches.append(nextcord.SelectOption(label=branch))
        self.select = nextcord.ui.StringSelect(
            placeholder="Select a branch", options=self.branches, row=1
        )
        self.add_item(self.select)

    @nextcord.ui.button(label="Continue", style=nextcord.ButtonStyle.green, row=2)
    async def finish(
        self, _button: nextcord.ui.Button, _interaction: nextcord.Interaction
    ):
        """Continues setup"""
        self.stop()


class TestCog(commands.Cog):
    def __init__(self, bot: nextcord.Client):
        self.bot: nextcord.Client = bot

    @nextcord.slash_command(name="test", guild_ids=TESTING_GUILDS)
    async def test(self, _interaction: nextcord.Interaction):
        """
        This is the main slash command that will be the prefix of all commands below.
        Also prefixes any test commands in other Cogs
        This will never get called since it has subcommands.
        """

    @test.subcommand(
        name="branch",
        description="Switch the branch that the test bot is deployed under.",
    )
    async def switch_branch(self, interaction: nextcord.Interaction):
        """Switches the branch that the test bot account is currently deployed off of."""
        await interaction.response.defer()
        if interaction.user.get_role(DEV_CONTRIBUTOR_ROLE) is None:
            await interaction.send(
                "You do not have the Contributors role and cannot run this command.",
                ephemeral=True,
            )
            return

        github_api = AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"bearer {GITHUB_API_KEY}"},
        )

        branch_names = []
        async with gql.Client(
            transport=github_api,
            fetch_schema_from_transport=False,
        ) as session:
            list_branches = gql.gql(
                """
                query getBranches {
                    repository(name: "pugBot", owner: "Ooglely") {
                        refs(first: 25, refPrefix: "refs/heads/") {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                    }
                }
                """
            )

            result = await session.execute(list_branches)
            for branch in result["repository"]["refs"]["edges"]:
                branch_names.append(branch["node"]["name"])
        branch_select = BranchSelect(branch_names)
        await interaction.send(
            "Select a branch to deploy.", view=branch_select, ephemeral=False
        )
        status = await branch_select.wait()
        if not status:
            selected_branch = branch_select.select.values[0]
            railway_api = AIOHTTPTransport(
                url="https://backboard.railway.app/graphql/v2",
                headers={"Authorization": f"Bearer {RAILWAY_API_KEY}"},
            )

            async with gql.Client(
                transport=railway_api,
                fetch_schema_from_transport=False,
            ) as session:
                set_deployment_trigger = gql.gql(
                    f"""
                    mutation setDeploymentTrigger {{
                        deploymentTriggerUpdate(
                            id: "275e3203-4ac7-4ada-84de-1c11f8b9b124",
                            input: {{
                                branch: "{selected_branch}",
                                checkSuites: true,
                                repository: "Ooglely/pugBot",
                            }}
                        ) {{
                            id
                        }}
                    }}
                    """
                )

                redeploy_environment = gql.gql(
                    """
                    mutation deployNewDeployment {
                        environmentTriggersDeploy(
                            input: {
                                environmentId: "5c2a716b-7bac-4dae-9ee4-78725cb1ee1a",
                                projectId: "8ffd3860-8187-406a-bf03-69d7356ec462",
                                serviceId: "01b0b783-64b1-4727-b8c9-5df09701c8ac"
                            }
                        )
                    }
                    """
                )

                await session.execute(set_deployment_trigger)
                await session.execute(redeploy_environment)
            await interaction.edit_original_message(
                content=f"Switching branch to `{selected_branch}`... Please check <#1144720434370203698> to see deployment progress.",
                view=None,
            )
