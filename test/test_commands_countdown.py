import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, ANY
from datetime import datetime, timedelta
import pytz
from huntbot.commands.countdown_commands import current_countdown
import logging
import re

@pytest.mark.asyncio
async def test_cog_missing():
    # Setup mocks
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = None  # Cog missing

    hunt_bot = MagicMock()

    # Call function
    await current_countdown(interaction, hunt_bot, discord_bot)

    # Should warn and send ephemeral message about no countdown
    discord_bot.get_cog.assert_called_once_with("CountdownCog")
    interaction.response.send_message.assert_awaited_once_with(
        "No countdown to display.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_hunt_not_started_future_countdown():
    # Setup mocks
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    tz = pytz.timezone("Europe/London")
    now = datetime.now(tz)
    start_time = now + timedelta(hours=2, minutes=30)

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = start_time

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    # Call function
    await current_countdown(interaction, hunt_bot, discord_bot)

    # Should call send_message with correct countdown message
    expected_message = f"\nThe Hunt begins in: 2 Hours and 30 Minutes\n"
    interaction.response.send_message.assert_awaited_once_with(expected_message, ephemeral=True)

@pytest.mark.asyncio
async def test_hunt_not_started_future_countdown():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    tz = pytz.timezone("Europe/London")
    now = datetime.now(tz)
    start_time = now + timedelta(hours=2, minutes=30)

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = start_time

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    # Get the message text sent
    message = interaction.response.send_message.call_args[0][0]

    # Parse the hours and minutes using regex
    match = re.search(r"(\d+) Hours and (\d+) Minutes", message)
    assert match is not None, "Countdown message did not contain expected format"

    hours = int(match.group(1))
    minutes = int(match.group(2))

    assert hours == 2
    assert 29 <= minutes <= 30  # Accept 1-minute drift

@pytest.mark.asyncio
@pytest.mark.parametrize("started, start_offset, end_offset", [
    (False, -1, None),  # Hunt not started but start time already passed
    (True, None, -1),   # Hunt started but end time already passed
])
async def test_hunt_already_ended(started, start_offset, end_offset):
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    tz = pytz.timezone("Europe/London")
    now = datetime.now(tz)

    hunt_bot = MagicMock()
    hunt_bot.started = started
    if start_offset is not None:
        hunt_bot.start_datetime = now + timedelta(hours=start_offset)
    else:
        hunt_bot.start_datetime = now - timedelta(hours=1)

    if end_offset is not None:
        hunt_bot.end_datetime = now + timedelta(hours=end_offset)
    else:
        hunt_bot.end_datetime = now - timedelta(hours=1)

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    expected_message = f"\nThe Hunt {'begins' if not started else 'ends'} in: 0 Hours and 0 Minutes\n"
    interaction.response.send_message.assert_awaited_once_with(expected_message, ephemeral=True)

@pytest.mark.asyncio
async def test_hunt_not_started_with_different_timezone():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    # Use UTC instead of Europe/London
    tz = pytz.UTC
    now = datetime.now(tz)
    start_time = now + timedelta(hours=3, minutes=45)

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = start_time

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    # Get the actual message sent
    message = interaction.response.send_message.call_args[0][0]

    assert "The Hunt begins in:" in message
    assert "3 Hours" in message
    # Accept 45 or 44 minutes, depending on drift
    assert any(minute in message for minute in ["45 Minutes", "44 Minutes"])


@pytest.mark.asyncio
async def test_countdown_is_exactly_now():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    tz = pytz.timezone("Europe/London")
    now = datetime.now(tz)

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = now

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    expected_message = f"\nThe Hunt begins in: 0 Hours and 0 Minutes\n"
    interaction.response.send_message.assert_awaited_once_with(expected_message, ephemeral=True)

@pytest.mark.asyncio
async def test_naive_datetime_handling():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    now = datetime.now()  # Naive datetime

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = now

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    interaction.response.send_message.assert_awaited_once_with(
        "Countdown time is not properly configured. Yell at Druid.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_countdown_message_format():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    tz = pytz.timezone("Europe/London")
    now = datetime.now(tz)
    start_time = now + timedelta(hours=1, minutes=10)

    hunt_bot = MagicMock()
    hunt_bot.started = False
    hunt_bot.start_datetime = start_time

    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = True

    await current_countdown(interaction, hunt_bot, discord_bot)

    message = interaction.response.send_message.call_args[0][0]

    # Regex to extract hours/minutes
    match = re.search(r"(\d+) Hours and (\d+) Minutes", message)
    assert match is not None, "Countdown message did not contain expected format"

    hours = int(match.group(1))
    minutes = int(match.group(2))

    assert hours == 1
    assert 9 <= minutes <= 10  # Allow 1-minute clock drift

@pytest.mark.asyncio
async def test_logging_when_cog_missing(caplog):
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    hunt_bot = MagicMock()
    discord_bot = MagicMock()
    discord_bot.get_cog.return_value = None

    with caplog.at_level(logging.WARNING):
        await current_countdown(interaction, hunt_bot, discord_bot)

    assert "CountdownCog not found" in caplog.text
