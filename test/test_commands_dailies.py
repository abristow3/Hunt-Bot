import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from huntbot.HuntBot import HuntBot
from huntbot.commands.dailies_command import (
    complete_daily, fetch_cog, check_user_roles,
    current_daily, update_daily_image, update_daily_description
)
from huntbot.cogs.Dailies import DailiesCog  # assuming your cog class is here


@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock()
    interaction.response = AsyncMock()
    return interaction


@pytest.fixture
def mock_admin_role():
    role = MagicMock()
    role.name = "Admin"
    return role


@pytest.fixture
def mock_hunt_bot():
    hunt_bot = MagicMock(spec=HuntBot)
    hunt_bot.team_one_name = "Red"
    hunt_bot.team_two_name = "Blue"
    # Add any other needed attributes here
    return hunt_bot


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.get_channel.return_value = MagicMock()
    bot.wait_until_ready = AsyncMock()
    return bot


@pytest.fixture
def mock_cog(mock_bot, mock_hunt_bot):
    # Create a real DailiesCog instance if available, else mock similar to your bounties example
    cog = DailiesCog(mock_bot, mock_hunt_bot)

    # Mock async methods to avoid real discord calls
    cog.update_embed_url = AsyncMock(return_value="Image updated")
    cog.update_embed_description = AsyncMock(return_value="Description updated")
    cog.post_daily_complete_message = AsyncMock()

    cog.daily_description = "@everyone Test daily"
    cog.first_place = ""
    cog.second_place = ""

    return cog


@pytest.fixture(autouse=True)
def patch_bot_get_cog(mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    yield


# === Tests ===

@pytest.mark.asyncio
async def test_fetch_cog_success(mock_interaction, mock_bot, mock_cog):
    result = await fetch_cog(mock_interaction, mock_bot, cog_name="DailiesCog", cog_type=DailiesCog)
    assert result == mock_cog


@pytest.mark.asyncio
async def test_fetch_cog_failure(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    result = await fetch_cog(mock_interaction, mock_bot, cog_name="DailiesCog", cog_type=DailiesCog)
    assert result is None
    mock_interaction.response.send_message.assert_called_with(
        "DailiesCog is not loaded or active.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_check_user_roles_success(mock_interaction, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    result = await check_user_roles(mock_interaction, authorized_roles=["admin"])
    assert result is True


@pytest.mark.asyncio
async def test_check_user_roles_failure(mock_interaction):
    mock_interaction.user.roles = []
    result = await check_user_roles(mock_interaction, authorized_roles=["admin"])
    assert result is False
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_current_daily_success(mock_interaction, mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    await current_daily(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "**Current Daily:**\nTest daily", ephemeral=True
    )


@pytest.mark.asyncio
async def test_current_daily_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await current_daily(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "DailiesCog is not loaded or active.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_image_success(mock_interaction, mock_bot, mock_cog, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_image(mock_interaction, mock_bot, url="https://img.com/image.png")
    mock_cog.update_embed_url.assert_called_once()
    mock_interaction.response.send_message.assert_called_with("Image updated", ephemeral=True)


@pytest.mark.asyncio
async def test_update_daily_image_permission_denied(mock_interaction, mock_bot, mock_cog):
    mock_interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_image(mock_interaction, mock_bot, url="https://img.com/image.png")
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_image_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await update_daily_image(mock_interaction, mock_bot, url="https://img.com/image.png")
    mock_interaction.response.send_message.assert_called_with(
        "DailiesCog is not loaded or active.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_description_success(mock_interaction, mock_bot, mock_cog, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_description(mock_interaction, "New description", mock_bot)
    mock_cog.update_embed_description.assert_called_once_with(new_desc="New description")
    mock_interaction.response.send_message.assert_called_with("Description updated", ephemeral=True)


@pytest.mark.asyncio
async def test_update_daily_description_permission_denied(mock_interaction, mock_bot, mock_cog):
    mock_interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_description(mock_interaction, "New description", mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_description_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await update_daily_description(mock_interaction, "New description", mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "DailiesCog is not loaded or active.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_complete_daily_first_place(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock(name="staff", spec=["name"])
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Red",
        hunt_bot=mock_hunt_bot
    )

    assert mock_cog.first_place == "Red"
    mock_cog.post_daily_complete_message.assert_awaited_with(team_name="Red", placement="First")
    mock_interaction.response.send_message.assert_called_with(
        "First place completion message posted succesfully for Red", ephemeral=True
    )


@pytest.mark.asyncio
async def test_complete_daily_second_place(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    mock_cog.first_place = "Red"
    mock_cog.second_place = ""

    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock(name="staff", spec=["name"])
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Blue",
        hunt_bot=mock_hunt_bot
    )

    assert mock_cog.second_place == "Blue"
    mock_cog.post_daily_complete_message.assert_awaited_with(team_name="Blue", placement="Second")
    mock_interaction.response.send_message.assert_called_with(
        "Second place completion message posted succesfully for Blue", ephemeral=True
    )


@pytest.mark.asyncio
async def test_complete_daily_already_claimed(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    mock_cog.first_place = "Red"
    mock_cog.second_place = "Blue"

    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock(name="staff", spec=["name"])
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Green",
        hunt_bot=mock_hunt_bot
    )

    mock_cog.post_daily_complete_message.assert_not_awaited()
    mock_interaction.response.send_message.assert_called_with(
        "First and Second place already claimed for the daily", ephemeral=True
    )
