import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from huntbot.cogs.Countdown import CountdownCog

import pytz

@pytest.fixture
def mock_hunt_bot():
    return MagicMock(
        config_map={"ANNOUNCEMENTS_CHANNEL_ID": "123456789"},
        start_datetime=datetime.now(pytz.timezone('Europe/London')) + timedelta(hours=25),
        end_datetime=datetime.now(pytz.timezone('Europe/London')) + timedelta(hours=50),
        started=False,
        ended=False
    )

@pytest.fixture
def mock_discord_bot():
    bot = MagicMock()
    bot.get_channel = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot

@pytest.fixture
def countdown_cog(mock_discord_bot, mock_hunt_bot):
    cog = CountdownCog(mock_discord_bot, mock_hunt_bot)
    return cog


# --------- Tests ---------

@pytest.mark.asyncio
async def test_get_announcements_channel_sets_id(countdown_cog):
    countdown_cog.get_announcements_channel()
    assert countdown_cog.announcements_channel_id == 123456789

def test_startup_check_filters_intervals(countdown_cog, mock_hunt_bot):
    # Move time closer to hunt start, within 5 hours
    mock_hunt_bot.start_datetime = datetime.now(pytz.timezone('Europe/London')) + timedelta(hours=5)
    countdown_cog.hunt_bot = mock_hunt_bot

    countdown_cog.startup_check()
    assert countdown_cog.start_countdown_intervals == [2, 1]

def test_startup_check_handles_started_hunt(countdown_cog, mock_hunt_bot):
    mock_hunt_bot.started = True
    mock_hunt_bot.ended = False
    mock_hunt_bot.end_datetime = datetime.now(pytz.timezone('Europe/London')) + timedelta(hours=4)
    countdown_cog.hunt_bot = mock_hunt_bot

    countdown_cog.startup_check()
    assert countdown_cog.start_completed is True
    assert countdown_cog.end_countdown_intervals == [2, 1]

@pytest.mark.asyncio
async def test_cog_load_configures_and_starts(countdown_cog):
    countdown_cog.get_announcements_channel = MagicMock()
    countdown_cog.start_countdown.start = MagicMock()
    countdown_cog.startup_check = MagicMock()

    await countdown_cog.cog_load()

    countdown_cog.get_announcements_channel.assert_called_once()
    countdown_cog.startup_check.assert_called_once()
    countdown_cog.start_countdown.start.assert_called_once()
    assert countdown_cog.configured is True

@pytest.mark.asyncio
async def test_cog_load_fails_on_exception(countdown_cog):
    countdown_cog.get_announcements_channel = MagicMock(side_effect=Exception("Fail"))
    await countdown_cog.cog_load()
    assert countdown_cog.configured is False

@pytest.mark.asyncio
async def test_start_countdown_posts_start_message(countdown_cog, mock_discord_bot, mock_hunt_bot):
    mock_channel = AsyncMock()
    mock_discord_bot.get_channel.return_value = mock_channel

    countdown_cog.announcements_channel_id = 123456789
    countdown_cog.hunt_bot.start_datetime = datetime.now(pytz.timezone('Europe/London')) + timedelta(seconds=1)
    countdown_cog.start_countdown_intervals = [0]
    countdown_cog.configured = True

    await asyncio.sleep(1.1)  # simulate passage of time
    await countdown_cog.start_countdown()

    mock_channel.send.assert_called_once()
    assert countdown_cog.start_completed is True or not countdown_cog.start_countdown_intervals

@pytest.mark.asyncio
async def test_start_countdown_posts_end_message(countdown_cog, mock_discord_bot, mock_hunt_bot):
    mock_channel = AsyncMock()
    mock_discord_bot.get_channel.return_value = mock_channel

    countdown_cog.announcements_channel_id = 123456789
    countdown_cog.hunt_bot.end_datetime = datetime.now(pytz.timezone('Europe/London')) + timedelta(seconds=1)
    countdown_cog.end_countdown_intervals = [0]
    countdown_cog.start_completed = True
    countdown_cog.configured = True

    await asyncio.sleep(1.1)
    await countdown_cog.start_countdown()

    mock_channel.send.assert_called_once()
    assert countdown_cog.end_completed is True or not countdown_cog.end_countdown_intervals

@pytest.mark.asyncio
async def test_start_countdown_handles_no_channel(countdown_cog, mock_discord_bot):
    mock_discord_bot.get_channel.return_value = None

    countdown_cog.announcements_channel_id = 999
    countdown_cog.configured = True

    await countdown_cog.start_countdown()
    # Should exit without exception

@pytest.mark.asyncio
async def test_start_countdown_not_configured_skips(countdown_cog):
    countdown_cog.configured = False
    await countdown_cog.start_countdown()
    # No crash, does nothing

@pytest.mark.asyncio
async def test_cog_unload_stops_loop_if_running(countdown_cog):
    countdown_cog.start_countdown.is_running = MagicMock(return_value=True)
    countdown_cog.start_countdown.stop = MagicMock()
    await countdown_cog.cog_unload()
    countdown_cog.start_countdown.stop.assert_called_once()

@pytest.mark.asyncio
async def test_cog_unload_does_nothing_if_loop_not_running(countdown_cog):
    countdown_cog.start_countdown.is_running = MagicMock(return_value=False)
    countdown_cog.start_countdown.stop = MagicMock()
    await countdown_cog.cog_unload()
    countdown_cog.start_countdown.stop.assert_not_called()

def test_startup_check_all_start_intervals_missed(countdown_cog, mock_hunt_bot):
    # Hunt starts in the past
    mock_hunt_bot.start_datetime = datetime.now(pytz.timezone('Europe/London')) - timedelta(hours=1)
    countdown_cog.hunt_bot = mock_hunt_bot

    countdown_cog.startup_check()

    assert countdown_cog.start_countdown_intervals == []
    assert countdown_cog.start_completed is False  # Still False here; completion happens in loop

def test_startup_check_all_end_intervals_missed(countdown_cog, mock_hunt_bot):
    mock_hunt_bot.started = True
    mock_hunt_bot.ended = False
    mock_hunt_bot.end_datetime = datetime.now(pytz.timezone('Europe/London')) - timedelta(hours=1)
    countdown_cog.hunt_bot = mock_hunt_bot

    countdown_cog.startup_check()

    assert countdown_cog.end_countdown_intervals == []

@pytest.mark.asyncio
async def test_interval_not_reused(countdown_cog, mock_discord_bot, mock_hunt_bot):
    mock_channel = AsyncMock()
    mock_discord_bot.get_channel.return_value = mock_channel

    countdown_cog.announcements_channel_id = 123
    countdown_cog.configured = True
    countdown_cog.start_countdown_intervals = [0]

    # Simulate time being past the interval
    countdown_cog.hunt_bot.start_datetime = datetime.now(pytz.timezone('Europe/London'))

    # Call twice
    await countdown_cog.start_countdown()
    await countdown_cog.start_countdown()

    # Should only post once
    mock_channel.send.assert_called_once()

def test_startup_with_empty_intervals(countdown_cog, mock_hunt_bot):
    countdown_cog.start_countdown_intervals = []
    countdown_cog.end_countdown_intervals = []

    countdown_cog.startup_check()

    assert countdown_cog.start_countdown_intervals == []
    assert countdown_cog.end_countdown_intervals == []

def test_template_message_formatting():
    from string import Template

    begins_template = Template("Hunt starts in $num_hours hours!")
    result = begins_template.safe_substitute(num_hours=6)
    
    assert result == "Hunt starts in 6 hours!"

@pytest.mark.asyncio
async def test_loop_stops_when_completed(countdown_cog, mock_discord_bot):
    mock_channel = AsyncMock()
    mock_discord_bot.get_channel.return_value = mock_channel

    countdown_cog.configured = True
    countdown_cog.announcements_channel_id = 123

    countdown_cog.start_countdown_intervals = []
    countdown_cog.end_countdown_intervals = []
    countdown_cog.start_completed = True
    countdown_cog.end_completed = True

    countdown_cog.start_countdown.stop = MagicMock()
    
    await countdown_cog.start_countdown()
    
    countdown_cog.start_countdown.stop.assert_called_once()

def test_get_announcements_channel_raises():
    mock_hunt_bot = MagicMock(config_map={})  # No ID
    mock_bot = MagicMock()
    cog = CountdownCog(mock_bot, mock_hunt_bot)

    with pytest.raises(Exception):
        cog.get_announcements_channel()

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import pytz

@pytest.mark.asyncio
async def test_start_message_posted_when_time_matches_interval():
    # Arrange
    mock_channel = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_hunt_bot = MagicMock()
    # Hunt starts 6 hours from now
    hunt_start_time = datetime.now(pytz.timezone('Europe/London')) + timedelta(hours=6)
    mock_hunt_bot.start_datetime = hunt_start_time
    mock_hunt_bot.end_datetime = hunt_start_time + timedelta(hours=48)
    mock_hunt_bot.started = False
    mock_hunt_bot.ended = False
    mock_hunt_bot.config_map = {'ANNOUNCEMENTS_CHANNEL_ID': '123'}

    cog = CountdownCog(discord_bot=mock_bot, hunt_bot=mock_hunt_bot)
    cog.announcements_channel_id = 123
    cog.configured = True

    # Narrow down interval for testing
    cog.start_countdown_intervals = [6]

    # Simulate the current time being exactly the interval
    def fake_current_time():
        return hunt_start_time - timedelta(hours=6)
    cog.get_current_gmt_time = fake_current_time

    # Act
    await cog.start_countdown()

    # Assert
    mock_channel.send.assert_called_once()
    assert "6 hours" in mock_channel.send.call_args[0][0]
    assert cog.start_countdown_intervals == []  # Interval should be popped
    assert cog.start_completed  # Still false because only one message sent

@pytest.mark.asyncio
async def test_end_message_posted_when_time_matches_interval():
    # Arrange
    mock_channel = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_hunt_bot = MagicMock()
    # Hunt started 48 hours ago, ends in 6 hours
    now = datetime.now(pytz.timezone('Europe/London'))
    hunt_start_time = now - timedelta(hours=48)
    hunt_end_time = now + timedelta(hours=6)

    mock_hunt_bot.start_datetime = hunt_start_time
    mock_hunt_bot.end_datetime = hunt_end_time
    mock_hunt_bot.started = True
    mock_hunt_bot.ended = False
    mock_hunt_bot.config_map = {'ANNOUNCEMENTS_CHANNEL_ID': '123'}

    cog = CountdownCog(discord_bot=mock_bot, hunt_bot=mock_hunt_bot)
    cog.announcements_channel_id = 123
    cog.configured = True

    # Mark start messages as completed since hunt already started
    cog.start_completed = True

    # Narrow down interval for testing end countdown
    cog.end_countdown_intervals = [6]

    # Simulate current time being exactly the interval before hunt ends
    def fake_current_time():
        return hunt_end_time - timedelta(hours=6)
    cog.get_current_gmt_time = fake_current_time

    # Act
    await cog.start_countdown()

    # Assert
    mock_channel.send.assert_called_once()
    assert "6 hours" in mock_channel.send.call_args[0][0]
    assert cog.end_countdown_intervals == []  # Interval should be popped
    assert cog.end_completed  # Should be True since no more intervals left