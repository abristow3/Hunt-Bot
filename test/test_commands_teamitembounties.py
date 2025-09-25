import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from huntbot.HuntBot import HuntBot
from huntbot.cogs.TeamItemBounty import TeamItemBountyCog
from huntbot.commands.command_utils import fetch_cog
import discord


# === Fixtures ===

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.channel = MagicMock()
    interaction.channel.id = 111111111  # Red team channel
    interaction.channel_id = 111111111
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_hunt_bot():
    hunt_bot = MagicMock(spec=HuntBot)
    hunt_bot.config_map = {
        'BOUNTIES_PER_DAY': '1',
        'BOUNTY_CHANNEL_ID': '123456789',
    }
    hunt_bot.pull_table_data.return_value = MagicMock(empty=False)
    hunt_bot.guild_id = 999999999
    hunt_bot.team_one_chat_channel_id = 111111111
    hunt_bot.team_two_chat_channel_id = 222222222
    hunt_bot.bounty_password = "fake_password"
    hunt_bot.team_one_name = "Red"
    hunt_bot.team_two_name = "Blue"
    return hunt_bot

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.get_channel.return_value = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot

@pytest.fixture
def mock_cog(mock_hunt_bot):
    cog = TeamItemBountyCog(mock_hunt_bot)
    cog.create_bounty = AsyncMock()
    cog.list_bounties = AsyncMock()
    cog.close_bounty = AsyncMock()
    cog.update_bounty = AsyncMock()
    return cog

@pytest.fixture(autouse=True)
def patch_bot_get_cog(mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    yield


# === Tests ===

@pytest.mark.asyncio
async def test_create_bounty_cmd_success(mock_interaction, mock_bot, mock_cog):
    with patch("huntbot.commands.command_utils.fetch_cog", new=AsyncMock(return_value=mock_cog)):
        cog = await fetch_cog(mock_interaction, mock_bot, "TeamItemBountyCog", TeamItemBountyCog)

        await mock_interaction.response.defer()
        await cog.create_bounty(mock_interaction, item_name="itemA", reward_amount="100k", time_limit_hours=24)

        mock_interaction.response.defer.assert_awaited_once()
        cog.create_bounty.assert_awaited_once_with(
            mock_interaction,
            item_name="itemA",
            reward_amount="100k",
            time_limit_hours=24
        )


@pytest.mark.asyncio
async def test_create_bounty_cmd_cog_none(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None  # Ensure no fallback cog

    with patch("huntbot.commands.command_utils.fetch_cog", new=AsyncMock(return_value=None)):
        cog = await fetch_cog(mock_interaction, mock_bot, "TeamItemBountyCog", TeamItemBountyCog)
        assert cog is None
        mock_interaction.response.defer.assert_not_called()


@pytest.mark.asyncio
async def test_list_bounties_cmd_success(mock_interaction, mock_bot, mock_cog):
    with patch("huntbot.commands.command_utils.fetch_cog", new=AsyncMock(return_value=mock_cog)):
        cog = await fetch_cog(mock_interaction, mock_bot, "TeamItemBountyCog", TeamItemBountyCog)

        await mock_interaction.response.defer()
        await cog.list_bounties(mock_interaction)

        mock_interaction.response.defer.assert_awaited_once()
        cog.list_bounties.assert_awaited_once_with(mock_interaction)


@pytest.mark.asyncio
async def test_close_bounty_cmd_success(mock_interaction, mock_bot, mock_cog):
    with patch("huntbot.commands.command_utils.fetch_cog", new=AsyncMock(return_value=mock_cog)):
        cog = await fetch_cog(mock_interaction, mock_bot, "TeamItemBountyCog", TeamItemBountyCog)

        await mock_interaction.response.defer()
        await cog.close_bounty(mock_interaction, item_name="itemA", completed_by="user123")

        mock_interaction.response.defer.assert_awaited_once()
        cog.close_bounty.assert_awaited_once_with(
            mock_interaction,
            item_name="itemA",
            completed_by="user123"
        )


@pytest.mark.asyncio
async def test_update_bounty_cmd_success(mock_interaction, mock_bot, mock_cog):
    with patch("huntbot.commands.command_utils.fetch_cog", new=AsyncMock(return_value=mock_cog)):
        cog = await fetch_cog(mock_interaction, mock_bot, "TeamItemBountyCog", TeamItemBountyCog)

        await mock_interaction.response.defer()
        await cog.update_bounty(mock_interaction, item_name="itemA", reward_amount="200k", time_limit_hours=12)

        mock_interaction.response.defer.assert_awaited_once()
        cog.update_bounty.assert_awaited_once_with(
            mock_interaction,
            item_name="itemA",
            reward_amount="200k",
            time_limit_hours=12
        )
