import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import discord
from discord.ext import commands
from collections.abc import AsyncIterator

from huntbot.exceptions import ConfigurationException
from huntbot.cogs.Memes import MemesCog


class AsyncMessageHistory(AsyncIterator):
    def __init__(self, messages):
        self._messages = messages
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        message = self._messages[self._index]
        self._index += 1
        return message


@pytest.fixture()
def bot():
    intents = discord.Intents.default()
    intents.messages = True
    intents.reactions = True
    intents.message_content = True  # Needed for testing on_message
    return commands.Bot(command_prefix="!", intents=intents)


@pytest.fixture()
def hunt_bot():
    mock_hunt = MagicMock()
    mock_hunt.config_map = {'MEME_CHANNEL_ID': "123456789"}
    mock_hunt.started = True
    mock_hunt.ended = False
    mock_hunt.start_datetime = discord.utils.snowflake_time(1)  # dummy datetime
    return mock_hunt


@pytest.fixture()
def cog(bot, hunt_bot):
    return MemesCog(bot, hunt_bot)


@pytest.mark.asyncio
async def test_initialize_meme_messages(cog):
    mock_channel = MagicMock(spec=discord.TextChannel)

    message1 = MagicMock()
    message1.attachments = [MagicMock(content_type="image/png")]
    message1.reactions = [MagicMock(count=3)]
    message1.id = 101

    message2 = MagicMock()
    message2.attachments = [MagicMock(content_type="video/mp4")]
    message2.reactions = [MagicMock(count=2)]
    message2.id = 102

    mock_channel.history = MagicMock(return_value=AsyncMessageHistory([message1, message2]))
    cog.bot.get_channel = MagicMock(return_value=mock_channel)
    cog.bot.wait_until_ready = AsyncMock()

    await cog.cog_load()

    assert cog.message_reactions[101] == 3
    assert cog.message_reactions[102] == 2


@pytest.mark.asyncio
async def test_on_raw_reaction_add(cog):
    message_id = 12345
    cog.message_reactions[message_id] = 1
    cog.meme_channel_id = 67890

    payload = MagicMock()
    payload.channel_id = cog.meme_channel_id
    payload.message_id = message_id

    await cog.on_raw_reaction_add(payload)

    assert cog.message_reactions[message_id] == 2


@pytest.mark.asyncio
async def test_on_raw_reaction_remove(cog):
    message_id = 12345
    cog.message_reactions[message_id] = 2
    cog.meme_channel_id = 67890

    payload = MagicMock()
    payload.channel_id = cog.meme_channel_id
    payload.message_id = message_id

    await cog.on_raw_reaction_remove(payload)

    assert cog.message_reactions[message_id] == 1


@pytest.mark.asyncio
async def test_on_raw_reaction_remove_does_not_go_below_zero(cog):
    message_id = 12345
    cog.message_reactions[message_id] = 0
    cog.meme_channel_id = 67890

    payload = MagicMock()
    payload.channel_id = cog.meme_channel_id
    payload.message_id = message_id

    await cog.on_raw_reaction_remove(payload)

    assert cog.message_reactions[message_id] == 0


@pytest.mark.asyncio
async def test_on_raw_message_delete_removes_tracked_message(cog):
    message_id = 99999
    cog.meme_channel_id = 1234
    cog.message_reactions[message_id] = 42

    payload = MagicMock()
    payload.channel_id = cog.meme_channel_id
    payload.message_id = message_id

    await cog.on_raw_message_delete(payload)

    assert message_id not in cog.message_reactions


@pytest.mark.asyncio
async def test_on_message_valid_meme(cog):
    message = MagicMock(spec=discord.Message)
    message.channel.id = cog.meme_channel_id
    message.attachments = [MagicMock(content_type="image/png")]
    message.id = 1234

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    await cog.on_message(message)

    assert cog.message_reactions.get(message.id) == 0


@pytest.mark.asyncio
async def test_on_message_invalid_meme(cog):
    # Wrong channel
    message_wrong_channel = MagicMock(spec=discord.Message)
    message_wrong_channel.channel.id = 9999
    message_wrong_channel.attachments = [MagicMock(content_type="image/png")]
    message_wrong_channel.id = 5678

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    await cog.on_message(message_wrong_channel)
    assert 5678 not in cog.message_reactions

    # No attachments
    message_invalid_attachments = MagicMock(spec=discord.Message)
    message_invalid_attachments.channel.id = cog.meme_channel_id
    message_invalid_attachments.attachments = []
    message_invalid_attachments.id = 91011

    await cog.on_message(message_invalid_attachments)
    assert 91011 not in cog.message_reactions


@pytest.mark.asyncio
async def test_on_message_no_attachments(cog):
    message = MagicMock()
    message.attachments = []
    message.channel.id = cog.meme_channel_id
    message.author.bot = False

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    result = await cog.on_message(message)
    assert result is None
    assert len(cog.message_reactions) == 0


@pytest.mark.asyncio
async def test_on_message_invalid_attachments(cog):
    message = MagicMock()
    invalid_attachment = MagicMock()
    invalid_attachment.content_type = "text/plain"
    invalid_attachment.filename = "file.txt"
    message.attachments = [invalid_attachment]
    message.id = 1234
    message.channel.id = cog.meme_channel_id
    message.author.bot = False

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    cog.message_reactions.clear()

    result = await cog.on_message(message)
    assert result is None
    assert len(cog.message_reactions) == 0


@pytest.mark.asyncio
async def test_on_message_mixed_attachments(cog):
    message = MagicMock()
    valid_attachment = MagicMock()
    valid_attachment.content_type = "image/jpeg"
    invalid_attachment = MagicMock()
    invalid_attachment.content_type = "text/plain"
    message.attachments = [invalid_attachment, valid_attachment]
    message.channel.id = cog.meme_channel_id
    message.author.bot = False

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    cog.bot.wait_until_ready = AsyncMock()

    await cog.on_message(message)
    assert message.id in cog.message_reactions


@pytest.mark.asyncio
async def test_on_message_ignores_if_hunt_not_started_or_ended(cog):
    for started, ended in [(False, False), (True, True), (False, True)]:
        message = MagicMock()
        message.channel.id = cog.meme_channel_id
        message.attachments = [MagicMock(content_type="image/png")]
        message.author.bot = False
        message.id = 5555

        cog.hunt_bot.started = started
        cog.hunt_bot.ended = ended
        cog.message_reactions.clear()

        await cog.on_message(message)
        assert 5555 not in cog.message_reactions


@pytest.mark.asyncio
async def test_on_message_attachment_no_content_type_valid_filename(cog):
    message = MagicMock()
    attachment = MagicMock()
    attachment.content_type = None
    attachment.filename = "valid_image.jpg"
    message.attachments = [attachment]
    message.channel.id = cog.meme_channel_id
    message.author.bot = False
    message.id = 6789

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    await cog.on_message(message)
    assert 6789 in cog.message_reactions


@pytest.mark.asyncio
async def test_on_message_all_invalid_attachments(cog):
    message = MagicMock()
    att1 = MagicMock(content_type="text/plain", filename="file.txt")
    att2 = MagicMock(content_type=None, filename="document.pdf")
    message.attachments = [att1, att2]
    message.channel.id = cog.meme_channel_id
    message.author.bot = False
    message.id = 9876

    cog.hunt_bot.started = True
    cog.hunt_bot.ended = False

    await cog.on_message(message)
    assert 9876 not in cog.message_reactions


@pytest.mark.asyncio
async def test_get_meme_channel_raises_config_exception():
    bot_mock = MagicMock()
    hunt_bot_mock = MagicMock()
    hunt_bot_mock.config_map = {}  # Missing MEME_CHANNEL_ID

    cog = MemesCog(bot_mock, hunt_bot_mock)

    with pytest.raises(ConfigurationException) as excinfo:
        await cog.cog_load()

    assert "MEME_CHANNEL_ID" in str(excinfo.value)



@pytest.mark.asyncio
async def test_initialize_meme_messages_invalid_channel(cog):
    cog.bot.get_channel = MagicMock(return_value=None)
    cog.bot.wait_until_ready = AsyncMock()
    await cog.initialize_meme_messages()
    assert len(cog.message_reactions) == 0


@pytest.mark.asyncio
async def test_post_top_memes_scoreboard_empty(cog):
    cog.message_reactions.clear()
    await cog.post_top_memes_scoreboard()


@pytest.mark.asyncio
async def test_post_top_memes_scoreboard_not_found_handling(cog):
    channel_mock = MagicMock(spec=discord.TextChannel)
    cog.bot.get_channel = MagicMock(return_value=channel_mock)
    cog.message_reactions = {123: 5}

    async def fetch_message(message_id):
        raise discord.NotFound(Mock(), "Not found")

    channel_mock.fetch_message = fetch_message
    await cog.post_top_memes_scoreboard()


@pytest.mark.asyncio
async def test_post_top_memes_scoreboard_posts_message_with_content(cog, caplog):
    cog.message_reactions = {111: 5, 222: 3, 333: 1}
    cog.meme_channel_id = 123456789

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()

    async def mock_fetch_message(message_id):
        mock_message = MagicMock()
        mock_message.author.id = 42
        mock_message.attachments = [
            MagicMock(content_type='image/png', url='http://fake.url/meme.png', filename='meme.png')
        ]
        return mock_message

    mock_channel.fetch_message = AsyncMock(side_effect=mock_fetch_message)

    with patch.object(cog.bot, 'get_channel', return_value=mock_channel) as mock_get_channel:
        with caplog.at_level("INFO"):
            await cog.post_top_memes_scoreboard()

        mock_get_channel.assert_called_once_with(cog.meme_channel_id)
        mock_channel.send.assert_awaited()


@pytest.mark.asyncio
async def test_post_top_memes_scoreboard_logs_when_no_memes(cog, caplog):
    cog.message_reactions.clear()
    cog.meme_channel_id = 123456789

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    cog.bot.get_channel = MagicMock(return_value=mock_channel)

    with caplog.at_level("INFO"):
        await cog.post_top_memes_scoreboard()

    found_info = any("No memes to post." in record.message for record in caplog.records)
    assert found_info
    mock_channel.send.assert_not_called()
