import discord
from discord import app_commands
import logging
from huntbot.cogs.TeamItemBounty import TeamItemBountyCog
from huntbot.commands.command_utils import fetch_cog
from discord.ext.commands import Bot

logger = logging.getLogger(__name__)


def register_team_item_bounty_commands(tree: app_commands.CommandTree, discord_bot: Bot) -> None:
    """
    Registers slash commands related to team item bounties with the given command tree.

    This function adds the following commands to the app_commands.CommandTree:
    - create_team_bounty: Create a new team bounty.
    - list_team_bounties: List all active team bounties.
    - close_team_bounty: Close an existing bounty early.
    - update_team_bounty: Update the reward and/or time limit of an active bounty.

    Args:
        tree (app_commands.CommandTree): The command tree to register the commands on.
        discord_bot (Bot): The discord.ext.commands.Bot instance to fetch cogs from.

    Returns:
        None
    """

    @tree.command(name="create_team_bounty", description="Create a new team bounty")
    @app_commands.describe(
        item_name="Name of the item",
        reward_amount="Reward amount",
        time_limit_hours="Time limit in hours (optional)"
    )
    async def create_bounty_cmd(interaction: discord.Interaction, item_name: str, reward_amount: str,
                                time_limit_hours: int = 48):
        """
        Command to create a new team bounty.

        Args:
            interaction (discord.Interaction): The interaction that triggered this command.
            item_name (str): The name of the item for the bounty.
            reward_amount (str): The reward amount for completing the bounty.
            time_limit_hours (int, optional): The time limit in hours for the bounty. Defaults to 48.

        Returns:
            None
        """
        cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot,
                              cog_name="TeamItemBountyCog", cog_type=TeamItemBountyCog)
        if cog is None:
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            logger.error("[CreateTeamItemBounty Command] Failed to defer interaction: already expired")
            return

        try:
            logger.info(f"[CreateTeamItemBounty Command] create command ran with: {item_name} {reward_amount} {time_limit_hours}")
            await cog.create_bounty(interaction, item_name=item_name, reward_amount=reward_amount,
                                              time_limit_hours=time_limit_hours)
        except Exception as e:
            logger.error("[CreateTeamItemBounty Command] Error running create bounty command", exc_info=e)
            await interaction.followup.send("Sorry, something went wrong while creating the team item bounty.", ephemeral=True)
            return

    @tree.command(name="list_team_bounties", description="Lists all team bounties.")
    async def list_bounties_cmd(interaction: discord.Interaction):
        """
        Command to list all current team bounties.

        Args:
            interaction (discord.Interaction): The interaction that triggered this command.

        Returns:
            None
        """
        logger.info(f"[ListTeamItemBounty Command] list command ran")

        cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot,
                              cog_name="TeamItemBountyCog", cog_type=TeamItemBountyCog)
        if cog is None:
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            logger.error("[ListTeamItemBounty Command] Failed to defer interaction: already expired")
            return

        try:
            await cog.list_bounties(interaction)
        except Exception as e:
            logger.error("[ListTeamItemBounty Command] Error running list team bounties command", exc_info=e)
            await interaction.followup.send("Sorry, something went wrong while listing team item bounties.", ephemeral=True)
            return

    @tree.command(name="close_team_bounty", description="Close a bounty early.")
    @app_commands.describe(
        item_name="The item name of the bounty",
        completed_by="The user who completed it"
    )
    async def close_bounty_cmd(interaction: discord.Interaction, item_name: str, completed_by: str):
        """
        Command to close an active team bounty early.

        Args:
            interaction (discord.Interaction): The interaction that triggered this command.
            item_name (str): The name of the bounty's item to close.
            completed_by (str): The user who completed the bounty.

        Returns:
            None
        """
        logger.info(f"[CloseTeamItemBounty Command] close bounty command ran with {item_name} {completed_by}")

        cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot,
                              cog_name="TeamItemBountyCog", cog_type=TeamItemBountyCog)
        if cog is None:
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            logger.error("[CloseTeamItemBounty Command] Failed to defer interaction: already expired")
            return

        try:
            await cog.close_bounty(interaction, item_name=item_name, completed_by=completed_by)
        except Exception as e:
            logger.error("[CloseTeamItemBounty Command] Error running close team bounty command", exc_info=e)
            await interaction.followup.send("Sorry, something went wrong while closing the bounty.", ephemeral=True)
            return

    @tree.command(name="update_team_bounty",
                  description="Update the reward value and/or time remaining for an active bounty.")
    @app_commands.describe(
        item_name="The item name of the bounty to update.",
        reward_amount="New reward amount (optional, e.g. 100k, 2M)",
        time_limit_hours="New time limit in hours (optional, e.g. 10, 15)"
    )
    async def update_bounty_cmd(interaction: discord.Interaction, item_name: str, reward_amount: str = "",
                                time_limit_hours: int = -100):
        """
        Command to update an active team bounty's reward and/or time limit.

        Args:
            interaction (discord.Interaction): The interaction that triggered this command.
            item_name (str): The name of the bounty's item to update.
            reward_amount (str, optional): The new reward amount. Defaults to an empty string (no update).
            time_limit_hours (int, optional): The new time limit in hours. Defaults to -100 (no update).

        Returns:
            None
        """
        logger.info(f"[UpdateTeamItemBounty Command] update bounty command ran with {item_name} {reward_amount} {time_limit_hours}")

        cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot,
                              cog_name="TeamItemBountyCog", cog_type=TeamItemBountyCog)
        if cog is None:
            return

        try:
            await interaction.response.defer()
        except discord.NotFound:
            logger.error("[UpdateTeamItemBounty Command] Failed to defer interaction: already expired")
            return

        try:
            await cog.update_bounty(interaction, item_name=item_name, reward_amount=reward_amount,
                                              time_limit_hours=time_limit_hours)
        except Exception as e:
            logger.error("[UpdateTeamItemBounty Command] Error running update team bounty command", exc_info=e)
            await interaction.followup.send("Sorry, something went wrong while updating the bounty.", ephemeral=True)
            return
