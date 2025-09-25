import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands, tasks

from huntbot.cogs.Score import ScoreCog, ConfigurationException, TableDataImportException

@pytest.fixture
def mock_discord_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.wait_until_ready = AsyncMock()
    bot.get_channel = MagicMock()
    return bot

@pytest.fixture
def mock_hunt_bot():
    bot = MagicMock()
    bot.config_map = {
        'ALERT_CHANNEL_ID': '999',
        'POINTS_CHANNEL_ID': '888',
    }
    bot.team_one_name = "Red"
    bot.team_two_name = "Blue"
    bot.pull_table_data = MagicMock()
    return bot

@pytest.fixture
def score_cog(mock_discord_bot, mock_hunt_bot):
    cog = ScoreCog(mock_discord_bot, mock_hunt_bot)
    return cog

@pytest.mark.asyncio
async def test_cog_load_success_starts_loops(score_cog):
    score_cog.get_score_channel = MagicMock()
    score_cog.get_alert_channel = MagicMock()
    score_cog.get_score_channel.return_value = None
    score_cog.get_alert_channel.return_value = None

    score_cog.start_scores.start = MagicMock()
    score_cog.watch_scores.start = MagicMock()

    await score_cog.cog_load()

    assert score_cog.configured is True
    score_cog.start_scores.start.assert_called_once()
    score_cog.watch_scores.start.assert_called_once()

@pytest.mark.asyncio
async def test_cog_load_configuration_exception(score_cog):
    score_cog.get_score_channel = MagicMock(side_effect=ConfigurationException(config_key='POINTS_CHANNEL_ID'))
    score_cog.get_alert_channel = MagicMock()
    score_cog.start_scores.start = MagicMock()
    score_cog.watch_scores.start = MagicMock()

    await score_cog.cog_load()

    # Should not start loops if exception raised
    assert score_cog.configured is False
    score_cog.start_scores.start.assert_not_called()
    score_cog.watch_scores.start.assert_not_called()

@pytest.mark.asyncio
async def test_cog_unload_stops_loops(score_cog):
    score_cog.start_scores.is_running = MagicMock(return_value=True)
    score_cog.watch_scores.is_running = MagicMock(return_value=True)
    score_cog.start_scores.stop = MagicMock()
    score_cog.watch_scores.stop = MagicMock()

    await score_cog.cog_unload()

    score_cog.start_scores.stop.assert_called_once()
    score_cog.watch_scores.stop.assert_called_once()

def test_get_alert_channel_success(score_cog):
    score_cog.hunt_bot.config_map['ALERT_CHANNEL_ID'] = '123'
    score_cog.get_alert_channel()
    assert score_cog.alert_channel_id == 123

def test_get_alert_channel_failure(score_cog):
    score_cog.hunt_bot.config_map['ALERT_CHANNEL_ID'] = '0'
    with pytest.raises(ConfigurationException):
        score_cog.get_alert_channel()

def test_get_score_channel_success(score_cog):
    score_cog.hunt_bot.config_map['POINTS_CHANNEL_ID'] = '456'
    score_cog.get_score_channel()
    assert score_cog.score_channel_id == 456

def test_get_score_channel_failure(score_cog):
    score_cog.hunt_bot.config_map['POINTS_CHANNEL_ID'] = '0'
    with pytest.raises(ConfigurationException):
        score_cog.get_score_channel()

def test_get_score_success(score_cog):
    # Setup dataframe mock
    import pandas as pd
    data = {
        'Team Name': [f"Team {score_cog.hunt_bot.team_one_name}", f"Team {score_cog.hunt_bot.team_two_name}"],
        'Total Points': [100, 200],
    }
    df = pd.DataFrame(data)

    score_cog.hunt_bot.pull_table_data.return_value = df

    score_cog.get_score()

    assert score_cog.team1_points == 100
    assert score_cog.team2_points == 200

def test_get_score_empty_dataframe_raises(score_cog):
    import pandas as pd
    empty_df = pd.DataFrame()
    score_cog.hunt_bot.pull_table_data.return_value = empty_df
    with pytest.raises(TableDataImportException):
        score_cog.get_score()

def test_determine_lead_team1_leads(score_cog):
    score_cog.team1_points = 10
    score_cog.team2_points = 5
    score_cog.determine_lead()
    assert "Red is ahead by 5 points" in score_cog.lead_message

def test_determine_lead_team2_leads(score_cog):
    score_cog.team1_points = 3
    score_cog.team2_points = 8
    score_cog.determine_lead()
    assert "Blue is ahead by 5 points" in score_cog.lead_message

def test_determine_lead_tie(score_cog):
    score_cog.team1_points = 7
    score_cog.team2_points = 7
    score_cog.determine_lead()
    assert score_cog.lead_message == "It's a tie!"

@pytest.mark.asyncio
async def test_start_scores_updates_message_success(score_cog):
    # Mark configured
    score_cog.configured = True
    # Setup mock channel & message
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel
    score_cog.message = AsyncMock()
    score_cog.message.edit = AsyncMock()

    # Setup score retrieval & lead
    score_cog.get_score = MagicMock()
    score_cog.determine_lead = MagicMock()
    score_cog.team1_points = 50
    score_cog.team2_points = 40
    score_cog.lead_message = "Lead message"

    await score_cog.start_scores()

    score_cog.get_score.assert_called_once()
    score_cog.determine_lead.assert_called_once()
    score_cog.message.edit.assert_awaited_once_with(content=score_cog.score_message)
    assert "Team Red: 50" in score_cog.score_message
    assert "Team Blue: 40" in score_cog.score_message
    assert score_cog.alert_sent is False
    assert score_cog.score_crash_count == 0

@pytest.mark.asyncio
async def test_start_scores_channel_not_found(score_cog):
    score_cog.configured = True
    score_cog.discord_bot.get_channel.return_value = None

    await score_cog.start_scores()

    # Should not raise and should skip update
@pytest.mark.asyncio
async def test_start_scores_message_notfound_sends_new(score_cog):
    score_cog.configured = True
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel
    # Create a mock response object with .status to prevent AttributeError
    mock_response = MagicMock()
    mock_response.status = 404

    score_cog.message = AsyncMock()
    score_cog.message.edit = AsyncMock(side_effect=discord.NotFound(response=mock_response, message=None))

    channel.send = AsyncMock()
    score_cog.get_score = MagicMock()
    score_cog.determine_lead = MagicMock()
    score_cog.team1_points = 20
    score_cog.team2_points = 10
    score_cog.lead_message = "Lead message"

    await score_cog.start_scores()

    channel.send.assert_awaited_once()
    assert score_cog.message == channel.send.return_value


@pytest.mark.asyncio
async def test_start_scores_get_score_raises(score_cog):
    score_cog.configured = True
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel
    score_cog.get_score = MagicMock(side_effect=TableDataImportException("score"))
    score_cog.determine_lead = MagicMock()

    await score_cog.start_scores()

    score_cog.determine_lead.assert_not_called()

@pytest.mark.asyncio
async def test_start_scores_generic_exception_sends_alert(score_cog):
    score_cog.configured = True
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel

    async def raise_exc():
        raise Exception("Boom")

    score_cog.get_score = MagicMock(side_effect=Exception("Boom"))
    score_cog.determine_lead = MagicMock()
    score_cog.message = AsyncMock()
    score_cog.message.edit = AsyncMock()
    score_cog.send_crash_alert = AsyncMock()

    # Alert not sent yet
    score_cog.alert_sent = False
    score_cog.score_crash_count = 0

    await score_cog.start_scores()

    assert score_cog.score_crash_count == 1
    score_cog.send_crash_alert.assert_awaited_once()
    assert score_cog.alert_sent is True

@pytest.mark.asyncio
async def test_before_start_scores_awaits_wait_until_ready(score_cog):
    score_cog.discord_bot.wait_until_ready = AsyncMock()
    await score_cog.before_start_scores()
    score_cog.discord_bot.wait_until_ready.assert_awaited_once()

@pytest.mark.asyncio
async def test_watch_scores_restarts_loop(score_cog):
    score_cog.start_scores.is_running = MagicMock(return_value=False)
    score_cog.start_scores.start = MagicMock()
    await score_cog.watch_scores()
    score_cog.start_scores.start.assert_called_once()

@pytest.mark.asyncio
async def test_watch_scores_loop_running(score_cog):
    score_cog.start_scores.is_running = MagicMock(return_value=True)
    score_cog.start_scores.start = MagicMock()
    await score_cog.watch_scores()
    score_cog.start_scores.start.assert_not_called()

@pytest.mark.asyncio
async def test_before_watch_scores_awaits_wait_until_ready(score_cog):
    score_cog.discord_bot.wait_until_ready = AsyncMock()
    await score_cog.before_watch_scores()
    score_cog.discord_bot.wait_until_ready.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_crash_alert_success(score_cog):
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel
    channel.send = AsyncMock()

    await score_cog.send_crash_alert("Error message")
    channel.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_send_crash_alert_channel_none(score_cog):
    score_cog.discord_bot.get_channel.return_value = None
    # Should not raise
    await score_cog.send_crash_alert("Error message")

@pytest.mark.asyncio
async def test_send_crash_alert_send_raises_logs_error(score_cog, caplog):
    channel = AsyncMock()
    score_cog.discord_bot.get_channel.return_value = channel
    channel.send = AsyncMock(side_effect=Exception("send fail"))

    with caplog.at_level("ERROR"):
        await score_cog.send_crash_alert("Error message")

    assert any("Failed to send crash alert to Discord" in m for m in caplog.messages)
