import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands, tasks
import pandas as pd
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
        'POINTS_CHANNEL_ID': '888',
    }
    bot.team_one_name = "Red"
    bot.team_two_name = "Blue"
    bot.pull_table_data = MagicMock()
    return bot


@pytest.fixture
def mock_gdoc():
    gdoc = MagicMock()
    gdoc.wait_until_ready = AsyncMock()
    gdoc.get_channel = MagicMock()
    return gdoc


@pytest.fixture
def score_cog(mock_discord_bot, mock_hunt_bot, mock_gdoc):
    cog = ScoreCog(mock_discord_bot, mock_hunt_bot, mock_gdoc)
    return cog


@pytest.mark.asyncio
async def test_cog_load_success_starts_loops(score_cog):
    score_cog.get_score_channel = MagicMock()
    score_cog.get_score_channel.return_value = None

    score_cog.start_scores.start = MagicMock()
    await score_cog.cog_load()

    assert score_cog.configured is True
    score_cog.start_scores.start.assert_called_once()


@pytest.mark.asyncio
async def test_cog_load_configuration_exception(score_cog):
    score_cog.get_score_channel = MagicMock(side_effect=ConfigurationException(config_key='POINTS_CHANNEL_ID'))
    score_cog.start_scores.start = MagicMock()
    await score_cog.cog_load()

    # Should not start loops if exception raised
    assert score_cog.configured is False
    score_cog.start_scores.start.assert_not_called()


@pytest.mark.asyncio
async def test_cog_unload_stops_loops(score_cog):
    score_cog.start_scores.is_running = MagicMock(return_value=True)
    score_cog.start_scores.stop = MagicMock()
    await score_cog.cog_unload()

    score_cog.start_scores.stop.assert_called_once()


def test_get_score_channel_success(score_cog):
    score_cog.hunt_bot.config_map['POINTS_CHANNEL_ID'] = '456'
    score_cog.get_score_channel()
    assert score_cog.score_channel_id == 456


def test_get_score_channel_failure(score_cog):
    score_cog.hunt_bot.config_map['POINTS_CHANNEL_ID'] = '0'
    with pytest.raises(ConfigurationException):
        score_cog.get_score_channel()


def test_get_score_success(score_cog):
    # Mock dataframe as GDoc.extract_table expects
    data = [
        ["Current Score", None],                 # merged header row
        ["Team Name", "Total Points"],           # column headers
        [f"Team {score_cog.hunt_bot.team_one_name}", 100],
        [f"Team {score_cog.hunt_bot.team_two_name}", 200]
    ]
    df = pd.DataFrame(data)

    score_cog.hunt_bot.sheet_data = df.copy()
    score_cog.hunt_bot.table_map = {
        "Current Score": {"start_col": 0, "end_col": len(df[0]) - 1}
    }

    score_cog.get_score()

    assert score_cog.team1_points == 100
    assert score_cog.team2_points == 200


def test_get_score_empty_dataframe_raises(score_cog):
    # Mock dataframe with only header row (no data)
    df = pd.DataFrame([
        ["Current Score", None],
        ["Team Name", "Total Points"]
    ])

    score_cog.hunt_bot.sheet_data = df
    score_cog.hunt_bot.table_map = {
        "Current Score": {"start_col": 0, "end_col": len(df[0]) - 1}
    }

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
    assert score_cog.lead_message == "It's tied!"


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


@pytest.mark.asyncio
async def test_start_scores_channel_not_found(score_cog):
    score_cog.configured = True
    score_cog.discord_bot.get_channel.return_value = None

    await score_cog.start_scores()


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
async def test_before_start_scores_awaits_wait_until_ready(score_cog):
    score_cog.discord_bot.wait_until_ready = AsyncMock()
    await score_cog.before_start_scores()
    score_cog.discord_bot.wait_until_ready.assert_awaited_once()
