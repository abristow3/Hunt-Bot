import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from huntbot.commands.dailies_command import fetch_cog, check_user_roles, current_daily, update_daily_image, update_daily_description

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.user.roles = [MagicMock(name='admin', spec=['name'])]
    interaction.user.roles[0].name = "Admin"
    return interaction

@pytest.fixture
def mock_bot():
    return MagicMock()

@pytest.fixture
def mock_cog():
    cog = AsyncMock()
    cog.daily_description = "@everyone Do the daily thing!"
    cog.update_embed_url = AsyncMock(return_value="Image updated")
    cog.update_embed_description = AsyncMock(return_value="Description updated")
    return cog


# === fetch_cog ===

@pytest.mark.asyncio
async def test_fetch_cog_success(mock_interaction, mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    result = await fetch_cog(mock_interaction, mock_bot)
    assert result == mock_cog


@pytest.mark.asyncio
async def test_fetch_cog_failure(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    result = await fetch_cog(mock_interaction, mock_bot)
    assert result is None
    mock_interaction.response.send_message.assert_called_once_with(
        "Daily Cog is not loaded or active.", ephemeral=True
    )


# === check_user_roles ===

@pytest.mark.asyncio
async def test_check_user_roles_authorized(mock_interaction):
    result = await check_user_roles(mock_interaction)
    assert result is True


@pytest.mark.asyncio
async def test_check_user_roles_unauthorized():
    interaction = AsyncMock()
    interaction.user.roles = []
    result = await check_user_roles(interaction)
    assert result is False
    interaction.response.send_message.assert_called_once_with(
        "You do not have permission to use this command.", ephemeral=True
    )


# === current_daily ===

@pytest.mark.asyncio
async def test_current_daily_success(mock_interaction, mock_bot, mock_cog):
    mock_cog.daily_description = "@everyone Do the daily!"
    mock_bot.get_cog.return_value = mock_cog

    await current_daily(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_once_with(
        "**Current Daily:**\nDo the daily!", ephemeral=True
    )


@pytest.mark.asyncio
async def test_current_daily_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await current_daily(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_once_with(
        "Daily Cog is not loaded or active.", ephemeral=True
    )


# === update_daily_image ===

@pytest.mark.asyncio
async def test_update_daily_image_success(mock_interaction, mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_image(mock_interaction, mock_bot, url="https://img.com/image.png")
    mock_cog.update_embed_url.assert_awaited_once_with(new_url="https://img.com/image.png")
    mock_interaction.response.send_message.assert_called_once_with("Image updated", ephemeral=True)


@pytest.mark.asyncio
async def test_update_daily_image_permission_denied(mock_bot, mock_cog):
    interaction = AsyncMock()
    interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog

    await update_daily_image(interaction, mock_bot, url="https://img.com/image.png")
    interaction.response.send_message.assert_called_once_with(
        "You do not have permission to use this command.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_image_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await update_daily_image(mock_interaction, mock_bot, url="https://img.com/image.png")
    mock_interaction.response.send_message.assert_called_once_with(
        "Daily Cog is not loaded or active.", ephemeral=True
    )


# === update_daily_description ===

@pytest.mark.asyncio
async def test_update_daily_description_success(mock_interaction, mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    await update_daily_description(mock_interaction, "New description", mock_bot)
    mock_cog.update_embed_description.assert_awaited_once_with(new_desc="New description")
    mock_interaction.response.send_message.assert_called_once_with("Description updated", ephemeral=True)


@pytest.mark.asyncio
async def test_update_daily_description_permission_denied(mock_bot, mock_cog):
    interaction = AsyncMock()
    interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog

    await update_daily_description(interaction, "New description", mock_bot)
    interaction.response.send_message.assert_called_once_with(
        "You do not have permission to use this command.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_update_daily_description_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await update_daily_description(mock_interaction, "New description", mock_bot)
    mock_interaction.response.send_message.assert_called_once_with(
        "Daily Cog is not loaded or active.", ephemeral=True
    )
