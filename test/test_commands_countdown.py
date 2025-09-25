import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import discord
from discord.ext.commands import Bot
from huntbot.HuntBot import HuntBot
from huntbot.cogs.Countdown import CountdownCog
from huntbot.commands.command_utils import fetch_cog
from huntbot.commands.countdown_commands import current_countdown, register_countdown_commands

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.response = AsyncMock()
    return interaction

@pytest.fixture
def mock_hunt_bot():
    hunt_bot = MagicMock(spec=HuntBot)
    return hunt_bot

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=Bot)
    bot.wait_until_ready = AsyncMock()
    return bot

@pytest.fixture
def mock_cog(mock_bot, mock_hunt_bot):
    cog = CountdownCog(mock_bot, mock_hunt_bot)
    return cog


@pytest.mark.asyncio
async def test_current_countdown_no_cog(mock_interaction, mock_hunt_bot, mock_bot):
    mock_bot.get_cog.return_value = None
    await current_countdown(mock_interaction, mock_hunt_bot, mock_bot)
    mock_interaction.response.send_message.assert_called_with("CountdownCog is not available or misconfigured.", ephemeral=True)

@pytest.mark.asyncio
async def test_current_countdown_naive_start_datetime(mock_interaction, mock_hunt_bot, mock_bot):
    mock_hunt_bot.start_datetime = datetime(2025, 1, 1, 12, 0, 0)  # naive datetime
    mock_hunt_bot.started = False
    mock_bot.get_cog.return_value = MagicMock(spec=CountdownCog)

    with patch("huntbot.commands.countdown_commands.logger") as mock_logger:
        await current_countdown(mock_interaction, mock_hunt_bot, mock_bot)
        mock_logger.warning.assert_called_once_with("[Countdown Commands] Hunt start_datetime is naive (no timezone)")

    mock_interaction.response.send_message.assert_called_with("Countdown time is not properly configured. Yell at Druid.", ephemeral=True)

@pytest.mark.asyncio
async def test_current_countdown_before_start(mock_interaction, mock_hunt_bot, mock_bot):
    now = datetime.now(timezone.utc)
    mock_hunt_bot.start_datetime = now + timedelta(minutes=10)
    mock_hunt_bot.end_datetime = now + timedelta(hours=1)
    mock_hunt_bot.started = False
    mock_bot.get_cog.return_value = MagicMock(spec=CountdownCog)

    await current_countdown(mock_interaction, mock_hunt_bot, mock_bot)

    expected_msg = f"\nThe Hunt begins in: 0 Hours and 10 Minutes\n"
    mock_interaction.response.send_message.assert_called_with(expected_msg, ephemeral=True)

@pytest.mark.asyncio
async def test_current_countdown_after_start_before_end(mock_interaction, mock_hunt_bot, mock_bot):
    now = datetime(2025, 9, 25, 12, 0, 0, tzinfo=timezone.utc)  # Fixed known time

    mock_hunt_bot.start_datetime = now - timedelta(minutes=10)
    mock_hunt_bot.end_datetime = now + timedelta(minutes=50)
    mock_hunt_bot.started = True

    mock_bot.get_cog.return_value = MagicMock(spec=CountdownCog)

    with patch("huntbot.commands.countdown_commands.datetime") as mock_datetime:
        mock_datetime.now.return_value = now  # Freeze datetime.now() to our fixed now
        mock_datetime.now.return_value = now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)  # fallback for other calls

        await current_countdown(mock_interaction, mock_hunt_bot, mock_bot)

    expected_msg = "\nThe Hunt ends in: 0 Hours and 50 Minutes\n"
    mock_interaction.response.send_message.assert_called_with(expected_msg, ephemeral=True)

@pytest.mark.asyncio
async def test_current_countdown_after_end(mock_interaction, mock_hunt_bot, mock_bot):
    now = datetime.now(timezone.utc)
    mock_hunt_bot.start_datetime = now - timedelta(hours=2)
    mock_hunt_bot.end_datetime = now - timedelta(minutes=10)
    mock_hunt_bot.started = True
    mock_bot.get_cog.return_value = MagicMock(spec=CountdownCog)

    await current_countdown(mock_interaction, mock_hunt_bot, mock_bot)

    expected_msg = f"\nThe Hunt ends in: 0 Hours and 0 Minutes\n"
    mock_interaction.response.send_message.assert_called_with(expected_msg, ephemeral=True)

def test_register_countdown_commands_adds_command():
    tree = MagicMock()
    hunt_bot = MagicMock()
    discord_bot = MagicMock()

    register_countdown_commands(tree, hunt_bot, discord_bot)

    tree.command.assert_called_once_with(name="countdown", description="Show time remaining until the Hunt starts or ends")
