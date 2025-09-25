import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from huntbot.cogs.Score import ScoreCog
from huntbot.commands.score_commands import current_score, register_score_commands

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    return interaction

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.get_channel.return_value = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot

@pytest.fixture
def mock_cog(mock_bot):
    # Create a ScoreCog instance with mock bot and a mock HuntBot (minimal)
    mock_hunt_bot = MagicMock()
    mock_hunt_bot.team_one_name = "Red"
    mock_hunt_bot.team_two_name = "Blue"
    mock_hunt_bot.config_map = {
        'POINTS_CHANNEL_ID': '1234567890',
        'ALERT_CHANNEL_ID': '0987654321'
    }
    cog = ScoreCog(discord_bot=mock_bot, hunt_bot=mock_hunt_bot)
    
    # Set some default attributes
    cog.score_message = "Team Red: 10 | Team Blue: 8"
    cog.message = None
    
    # Patch async tasks so they don't run during tests
    cog.start_scores = AsyncMock()
    cog.watch_scores = AsyncMock()
    
    return cog

@pytest.fixture(autouse=True)
def patch_bot_get_cog(mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    yield

# --- Tests ---

@pytest.mark.asyncio
async def test_current_score_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await current_score(mock_interaction, discord_bot=mock_bot)
    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        "ScoreCog is not loaded or active.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_current_score_no_message(mock_interaction, mock_bot, mock_cog):
    mock_cog.score_message = None
    await current_score(mock_interaction, discord_bot=mock_bot)
    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        "Score is currently unavailable.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_current_score_with_message(mock_interaction, mock_bot, mock_cog):
    mock_cog.score_message = "Team Red: 5 | Team Blue: 3"
    await current_score(mock_interaction, discord_bot=mock_bot)
    mock_bot.get_cog.assert_called_once_with("ScoreCog")
    mock_interaction.response.send_message.assert_awaited_once_with(
        mock_cog.score_message, ephemeral=True
    )

def test_score_command_registered(mock_bot):
    mock_tree = MagicMock()
    register_score_commands(mock_tree, discord_bot=mock_bot)
    assert mock_tree.command.called

@pytest.mark.asyncio
async def test_current_score_send_message_raises(mock_interaction, mock_bot, mock_cog):
    mock_interaction.response.send_message.side_effect = Exception("Send failed")
    mock_cog.score_message = "Score: 100"
    with pytest.raises(Exception, match="Send failed"):
        await current_score(mock_interaction, discord_bot=mock_bot)

@pytest.mark.asyncio
async def test_current_score_response_is_ephemeral(mock_interaction, mock_bot, mock_cog):
    mock_cog.score_message = "Some score"
    await current_score(mock_interaction, discord_bot=mock_bot)
    mock_interaction.response.send_message.assert_awaited_once()
    _, kwargs = mock_interaction.response.send_message.await_args
    assert kwargs.get("ephemeral") is True
