import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from huntbot.cogs.TeamItemBounty import TeamItemBountyCog, TeamItemBounty


@pytest.fixture
def mock_hunt_bot():
    bot = MagicMock()
    bot.team_one_name = "Red"
    bot.team_two_name = "Blue"
    bot.team_one_chat_channel_id = 111
    bot.team_two_chat_channel_id = 222
    return bot

@pytest.fixture
def cog(mock_hunt_bot):
    return TeamItemBountyCog(mock_hunt_bot)

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.channel = MagicMock()
    interaction.user = MagicMock()
    interaction.followup = AsyncMock()
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.user.roles = [MagicMock(name="Red team leader")]
    return interaction


# === TESTS ===

@pytest.mark.asyncio
async def test__is_duplicate_bounty_returns_true(cog):
    cog.active_bounties["Red"] = [
        TeamItemBounty(item_name="widget", reward_amount=100),
    ]
    assert cog._is_duplicate_bounty("Red", "WIDGET") is True

@pytest.mark.asyncio
async def test__is_duplicate_bounty_returns_false(cog):
    cog.active_bounties["Red"] = [
        TeamItemBounty(item_name="widget", reward_amount=100, time_limit_hours=24),
    ]
    cog.active_bounties["Red"][0].active = False  # inactive
    assert cog._is_duplicate_bounty("Red", "widget") is False


@pytest.mark.asyncio
async def test__parse_reward_amount_valid_k(cog, mock_interaction):
    result = await cog._parse_reward_amount(mock_interaction, "10k")
    assert result == 10_000

@pytest.mark.asyncio
async def test__parse_reward_amount_valid_m(cog, mock_interaction):
    result = await cog._parse_reward_amount(mock_interaction, "2.5M")
    assert result == 2_500_000

@pytest.mark.asyncio
async def test__parse_reward_amount_invalid(cog, mock_interaction):
    result = await cog._parse_reward_amount(mock_interaction, "notanumber")
    assert result is None
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test__parse_reward_amount_negative(cog, mock_interaction):
    result = await cog._parse_reward_amount(mock_interaction, "-100")
    assert result is None
    mock_interaction.followup.send.assert_awaited_once()


@pytest.mark.asyncio
async def test__check_user_roles_valid(cog, mock_interaction):
    mock_role = MagicMock()
    mock_role.name = "staff"
    mock_interaction.user.roles = [mock_role]

    result = await cog._check_user_roles(mock_interaction)
    assert result is True

@pytest.mark.asyncio
async def test__check_user_roles_invalid(cog, mock_interaction):
    mock_interaction.user.roles = [MagicMock(name="Member")]
    result = await cog._check_user_roles(mock_interaction)
    assert result is False
    mock_interaction.followup.send.assert_awaited_once()


@pytest.mark.asyncio
async def test__update_single_bounty_time_expired():
    bounty = TeamItemBounty(item_name="item", reward_amount=100, time_limit_hours=1)
    bounty.start_time = datetime.utcnow() - timedelta(hours=2)

    await TeamItemBountyCog._update_single_bounty_time(bounty)

    assert bounty.active is False
    assert bounty.time_remaining == 0

@pytest.mark.asyncio
async def test__update_single_bounty_time_active():
    bounty = TeamItemBounty(item_name="item", reward_amount=100, time_limit_hours=5)
    bounty.start_time = datetime.utcnow() - timedelta(hours=2)

    await TeamItemBountyCog._update_single_bounty_time(bounty)

    assert bounty.active is True
    assert 2.9 < bounty.time_remaining < 3.1


@pytest.mark.asyncio
async def test__create_bounty_table_empty(cog):
    message = await cog._create_bounty_table("Red")
    assert message.startswith("No bounties currently listed")


@pytest.mark.asyncio
async def test__create_bounty_table_with_data(cog):
    bounty = TeamItemBounty(item_name="sword", reward_amount=5000, time_limit_hours=10)
    cog.active_bounties["Red"] = [bounty]
    message = await cog._create_bounty_table("Red")

    assert "sword" in message
    assert "Active" in message
    assert "5,000" in message

import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_get_team_name_known_channel(mock_hunt_bot, cog):
    interaction = AsyncMock()
    interaction.channel_id = mock_hunt_bot.team_one_chat_channel_id
    team_name = await cog._get_team_name(interaction)
    assert team_name == mock_hunt_bot.team_one_name

    interaction.channel_id = mock_hunt_bot.team_two_chat_channel_id
    team_name = await cog._get_team_name(interaction)
    assert team_name == mock_hunt_bot.team_two_name

@pytest.mark.asyncio
async def test_get_team_name_unknown_channel_sends_error(cog):
    interaction = AsyncMock()
    interaction.channel_id = 999999  # unknown channel
    interaction.followup.send = AsyncMock()

    result = await cog._get_team_name(interaction)
    interaction.followup.send.assert_called_once_with("Error: Could not determine the correct team.", ephemeral=True)
    assert result is None

def test_is_duplicate_bounty_true(cog):
    team_name = cog.hunt_bot.team_one_name
    item_name = "Sword"
    cog.active_bounties[team_name] = [
        TeamItemBounty(item_name="sword", reward_amount=100, time_limit_hours=48)
    ]
    assert cog._is_duplicate_bounty(team_name, "Sword") is True
    assert cog._is_duplicate_bounty(team_name, "sWoRd") is True

def test_is_duplicate_bounty_false(cog):
    team_name = cog.hunt_bot.team_one_name
    cog.active_bounties[team_name] = [
        TeamItemBounty(item_name="shield", reward_amount=100)
    ]
    assert cog._is_duplicate_bounty(team_name, "sword") is False

import asyncio
from datetime import timedelta

@pytest.mark.asyncio
async def test_update_single_bounty_time_active_and_expired():
    bounty = TeamItemBounty("item", 100, time_limit_hours=1)
    bounty.start_time = bounty.start_time - timedelta(hours=0.5)
    await TeamItemBountyCog._update_single_bounty_time(bounty)
    assert 0 < bounty.time_remaining < 1
    assert bounty.active is True

    # Expire the bounty
    bounty.start_time = bounty.start_time - timedelta(hours=2)
    await TeamItemBountyCog._update_single_bounty_time(bounty)
    assert bounty.time_remaining == 0
    assert bounty.active is False

@pytest.mark.asyncio
async def test_update_single_bounty_time_inactive():
    bounty = TeamItemBounty("item", 100)
    bounty.active = False
    old_time_remaining = bounty.time_remaining
    await TeamItemBountyCog._update_single_bounty_time(bounty)
    assert bounty.time_remaining == old_time_remaining  # unchanged

@pytest.mark.asyncio
async def test_check_user_roles_permitted(cog):
    interaction = AsyncMock()
    role = AsyncMock()
    role.name = list(cog.target_roles)[0]
    interaction.user.roles = [role]
    interaction.followup.send = AsyncMock()

    result = await cog._check_user_roles(interaction)
    assert result is True
    interaction.followup.send.assert_not_called()

@pytest.mark.asyncio
async def test_check_user_roles_denied(cog):
    interaction = AsyncMock()
    role = AsyncMock()
    role.name = "randomrole"
    interaction.user.roles = [role]
    interaction.followup.send = AsyncMock()

    result = await cog._check_user_roles(interaction)
    assert result is False
    interaction.followup.send.assert_called_once_with("You don't have permission to run that command.", ephemeral=True)

@pytest.mark.asyncio
async def test_check_channel_id_valid(cog):
    interaction = AsyncMock()
    interaction.channel.id = cog.hunt_bot.team_one_chat_channel_id
    interaction.followup.send = AsyncMock()

    result = await cog._check_channel_id(interaction)
    assert result is True
    interaction.followup.send.assert_not_called()

@pytest.mark.asyncio
async def test_check_channel_id_invalid(cog):
    interaction = AsyncMock()
    interaction.channel.id = 123456
    interaction.followup.send = AsyncMock()

    result = await cog._check_channel_id(interaction)
    assert result is False

    interaction.followup.send.assert_called_once_with("This command can only be ran in the team chat channels", ephemeral=True)

@pytest.mark.asyncio
async def test_parse_reward_amount_valid(cog):
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    assert await cog._parse_reward_amount(interaction, "10") == 10
    assert await cog._parse_reward_amount(interaction, "1.5K") == 1500
    assert await cog._parse_reward_amount(interaction, "2M") == 2_000_000

@pytest.mark.asyncio
async def test_parse_reward_amount_negative(cog):
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    result = await cog._parse_reward_amount(interaction, "-10")
    interaction.followup.send.assert_called_once_with("Reward amount cannot be negative.", ephemeral=True)
    assert result is None

@pytest.mark.asyncio
async def test_parse_reward_amount_invalid(cog):
    interaction = AsyncMock()
    interaction.followup.send = AsyncMock()

    result = await cog._parse_reward_amount(interaction, "abc")
    interaction.followup.send.assert_called_once_with(
        "Reward amount must be a number (optionally with 'K' for thousand or 'M' for million).",
        ephemeral=True)
    assert result is None

import re

@pytest.mark.asyncio
async def test_create_bounty_table_no_bounties(cog):
    team_name = cog.hunt_bot.team_one_name
    cog.active_bounties[team_name] = []
    table = await cog._create_bounty_table(team_name)
    assert "No bounties currently listed" in table

@pytest.mark.asyncio
async def test_create_bounty_table_with_bounties(cog):
    team_name = cog.hunt_bot.team_one_name
    bounty = TeamItemBounty("testitem", 1000)
    cog.active_bounties[team_name] = [bounty]

    table = await cog._create_bounty_table(team_name)
    # Check header and bounty item in table
    assert "Item Name" in table
    assert "testitem" in table.lower()
    assert "Active" in table
    assert re.search(r"\|\s*testitem\s*\|", table.lower())
