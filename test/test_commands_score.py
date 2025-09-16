import pytest
from huntbot.commands.score_commands import current_score, register_score_commands
from unittest.mock import AsyncMock, MagicMock, patch
import discord

@pytest.mark.asyncio
async def test_current_score_no_cog():
    """Test when ScoreCog is not found."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.get_cog.return_value = None

    await current_score(mock_interaction, discord_bot=mock_bot)

    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        "No score to display.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_current_score_no_message():
    """Test when ScoreCog is found but has no score_message attribute."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    mock_cog = MagicMock()
    mock_cog.score_message = None  # Explicitly no message

    mock_bot = MagicMock()
    mock_bot.get_cog.return_value = mock_cog

    await current_score(mock_interaction, discord_bot=mock_bot)

    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        "Score is currently unavailable.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_current_score_with_message():
    """Test when ScoreCog has a valid score_message."""
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    test_message = "Team A: 5 | Team B: 3"

    mock_cog = MagicMock()
    mock_cog.score_message = test_message

    mock_bot = MagicMock()
    mock_bot.get_cog.return_value = mock_cog

    await current_score(mock_interaction, discord_bot=mock_bot)

    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        test_message, ephemeral=True
    )

def test_score_command_registered():
    mock_tree = MagicMock()
    mock_bot = MagicMock()

    # Call the function to register the command
    register_score_commands(mock_tree, discord_bot=mock_bot)

    # Assert a command was added to the tree
    assert mock_tree.command.called

@pytest.mark.asyncio
async def test_current_score_send_message_raises():
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.response.send_message.side_effect = Exception("Send failed")

    mock_cog = MagicMock()
    mock_cog.score_message = "Score: 100"

    mock_bot = MagicMock()
    mock_bot.get_cog.return_value = mock_cog

    with pytest.raises(Exception, match="Send failed"):
        await current_score(mock_interaction, discord_bot=mock_bot)

@pytest.mark.asyncio
async def test_current_score_response_is_ephemeral():
    mock_interaction = MagicMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    mock_cog = MagicMock()
    mock_cog.score_message = "Some score"

    mock_bot = MagicMock()
    mock_bot.get_cog.return_value = mock_cog

    await current_score(mock_interaction, discord_bot=mock_bot)

    mock_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_interaction.response.send_message.await_args
    assert kwargs.get("ephemeral") is True
