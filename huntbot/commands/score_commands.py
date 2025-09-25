import discord
from discord import app_commands
import logging
from discord.ext.commands import Bot
from huntbot.commands.command_utils import fetch_cog
from huntbot.cogs.Score import ScoreCog

logger = logging.getLogger(__name__)

async def current_score(interaction: discord.Interaction, discord_bot: Bot) -> None:
    """
    Sends the current score to the user via an ephemeral message.

    This function fetches the ScoreCog from the bot, retrieves the current score message,
    and responds to the interaction with that message. If the score message is not available,
    it sends a fallback message indicating unavailability.

    Args:
        interaction (discord.Interaction): The Discord interaction that triggered this call.
        discord_bot (Bot): The bot instance used to fetch the ScoreCog.

    Returns:
        None
    """
    cog = await fetch_cog(interaction=interaction, discord_bot=discord_bot, cog_name="ScoreCog", cog_type=ScoreCog)
    if cog is None:
        return

    message = getattr(cog, 'score_message', None)
    if not message:
        await interaction.response.send_message("Score is currently unavailable.", ephemeral=True)
        return

    await interaction.response.send_message(message, ephemeral=True)


def register_score_commands(tree: app_commands.CommandTree, discord_bot: Bot) -> None:
    """
    Registers the '/score' slash command to display the current score.

    This function adds a command to the provided command tree that, when called,
    logs the invocation and calls the `current_score` function to send the score message.

    Args:
        tree (app_commands.CommandTree): The command tree to register commands on.
        discord_bot (Bot): The Discord bot instance, used to fetch cogs as needed.

    Returns:
        None
    """
    @tree.command(name="score", description="List current score")
    async def score_cmd(interaction: discord.Interaction):
        """
        Handles the '/score' slash command by showing the current score.

        Args:
            interaction (discord.Interaction): The Discord interaction for this command.

        Returns:
            None
        """
        logger.info("[Score Commands] /score command called")
        await current_score(interaction, discord_bot=discord_bot)
