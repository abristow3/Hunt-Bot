import pytest
import time
import yaml
import random
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from discord.ext import commands
from huntbot.cogs.Memories import MemoriesCog
from huntbot.exceptions import ConfigurationException
import discord
import logging
from unittest.mock import Mock
import builtins


@pytest.fixture()
def bot():
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return commands.Bot(command_prefix="!", intents=intents)

@pytest.fixture()
def hunt_bot():
    mock_hunt = MagicMock()
    mock_hunt.config_map = {'GENERAL_CHANNEL_ID': "123456"}
    return mock_hunt

@pytest.fixture()
def cog(bot, hunt_bot):
    return MemoriesCog(bot, hunt_bot)


def test_get_general_channel_valid(cog):
    cog.hunt_bot.config_map['GENERAL_CHANNEL_ID'] = "123"
    cog.get_general_channel()
    assert cog.general_channel_id == 123

def test_get_general_channel_missing():
    bot = MagicMock()
    hunt_bot = MagicMock()
    hunt_bot.config_map = {}  # Missing GENERAL_CHANNEL_ID

    with pytest.raises(ConfigurationException) as excinfo:
        MemoriesCog(bot, hunt_bot).get_general_channel()

    assert "GENERAL_CHANNEL_ID" in str(excinfo.value)


def test_load_memories_from_file_valid(cog):
    test_yaml = """
    memories:
      - A fun moment from the hunt - Player1
      - Another cool thing - Player2
    """
    with patch("builtins.open", mock_open(read_data=test_yaml)):
        with patch("yaml.safe_load", return_value=yaml.safe_load(test_yaml)):
            cog.load_memories_from_file()

    assert len(cog.memories) == 2
    assert isinstance(cog.memory_iterator, type(iter([])))

def test_load_memories_from_file_empty(cog, caplog):
    test_yaml = "memories: []"
    with patch("builtins.open", mock_open(read_data=test_yaml)):
        with patch("yaml.safe_load", return_value=yaml.safe_load(test_yaml)):
            cog.load_memories_from_file()

    assert len(cog.memories) == 0
    assert "[Memories Cog] No memories found in the file." in caplog.text


def test_load_next_memory_valid(cog):
    cog.memories = ["A cool memory - Player1"]
    cog.memory_iterator = iter(cog.memories)

    result = cog.load_next_memory()
    assert result.startswith('"A cool memory"')
    assert result.endswith("— Player1")

def test_load_next_memory_no_player(cog):
    cog.memories = ["Just a fun moment"]
    cog.memory_iterator = iter(cog.memories)

    result = cog.load_next_memory()
    assert result.startswith('"Just a fun moment"')
    assert result.endswith("— Unknown")

def test_load_next_memory_exhausted(cog, caplog):
    caplog.set_level(logging.INFO)

    cog.memories = []
    cog.memory_iterator = iter(cog.memories)

    result = cog.load_next_memory()
    assert result is None
    assert "No more memories to load." in caplog.text

@pytest.mark.asyncio
async def test_cog_load_success(cog):
    cog.get_general_channel = MagicMock()
    cog.load_memories_from_file = MagicMock()
    cog.discord_bot.wait_until_ready = AsyncMock()
    cog.start_memories.start = MagicMock()

    await cog.cog_load()

    cog.get_general_channel.assert_called_once()
    cog.load_memories_from_file.assert_called_once()
    cog.discord_bot.wait_until_ready.assert_awaited_once()
    cog.start_memories.start.assert_called_once()


@pytest.mark.asyncio
async def test_cog_load_failure(caplog, cog):
    cog.get_general_channel = MagicMock(side_effect=Exception("fail"))
    cog.load_memories_from_file = MagicMock()
    cog.discord_bot.wait_until_ready = AsyncMock()
    cog.start_memories.start = MagicMock()

    await cog.cog_load()

    assert "Setup failed" in caplog.text
    assert "fail" in caplog.text


def test_cog_unload_stops_task(cog):
    cog.start_memories.cancel = MagicMock()
    cog.cog_unload()
    cog.start_memories.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_start_memories_posts_message(cog):
    cog.current_time_ms = 1000
    cog.next_memory_post_time_ms = 0  # So it will post

    cog.load_next_memory = Mock(return_value="Test memory message")

    mock_channel = AsyncMock()
    cog.discord_bot.get_channel = Mock(return_value=mock_channel)

    await cog.start_memories()  # <-- Proper way to call the loop

    mock_channel.send.assert_awaited_once_with("Test memory message")

@pytest.mark.asyncio
async def test_start_memories_channel_not_found(cog, caplog):
    cog.current_time_ms = 1000
    cog.next_memory_post_time_ms = 0
    cog.discord_bot.get_channel = Mock(return_value=None)

    with caplog.at_level("ERROR"):
        await cog.start_memories()

    assert "General Channel not found" in caplog.text

@pytest.mark.asyncio
async def test_start_memories_time_not_ready(cog):
    cog.current_time_ms = 1000
    cog.next_memory_post_time_ms = 5000  # Not ready yet

    mock_channel = AsyncMock()
    cog.discord_bot.get_channel = Mock(return_value=mock_channel)

    # Make load_next_memory return None so send is not called
    cog.load_next_memory = Mock(return_value=None)

    await cog.start_memories()

    mock_channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_memories_none_returned_stops_loop(cog):
    cog.current_time_ms = 1000
    cog.next_memory_post_time_ms = 0
    cog.load_next_memory = Mock(return_value=None)

    mock_channel = AsyncMock()
    cog.discord_bot.get_channel = Mock(return_value=mock_channel)

    # Patch the loop's stop method
    with patch.object(cog.start_memories, 'stop', wraps=cog.start_memories.stop) as mock_stop:
        await cog.start_memories()

        mock_stop.assert_called_once()
        mock_channel.send.assert_not_awaited()

@pytest.mark.asyncio
async def test_start_memories_exception_handling(cog, caplog):
    cog.current_time_ms = 1000
    cog.next_memory_post_time_ms = 0

    # Raise an exception in load_next_memory
    cog.load_next_memory = Mock(side_effect=Exception("Test exception"))

    mock_channel = AsyncMock()
    cog.discord_bot.get_channel = Mock(return_value=mock_channel)

    with patch.object(cog.start_memories, 'stop', wraps=cog.start_memories.stop) as mock_stop:
        with caplog.at_level("ERROR"):
            await cog.start_memories()

        assert "Error during task loop" in caplog.text
        mock_stop.assert_called_once()

def test_load_memories_file_not_found(cog, monkeypatch):
    def mock_open(*args, **kwargs):
        raise FileNotFoundError()
    monkeypatch.setattr(builtins, 'open', mock_open)

    with pytest.raises(FileNotFoundError):
        cog.load_memories_from_file()
