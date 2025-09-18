import pytest
from unittest.mock import AsyncMock, MagicMock
from huntbot.commands.bounties_command import fetch_cog, current_bounty, update_bounty_image, update_bounty_description, check_user_roles
import discord
from unittest.mock import AsyncMock, MagicMock


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
def mock_bot():
    return MagicMock()

@pytest.fixture
def mock_cog():
    cog = AsyncMock()
    cog.bounty_description = "@everyone Test bounty"
    cog.update_embed_url.return_value = "Image updated"
    cog.update_embed_description.return_value = "Description updated"
    return cog

# -------------------- Tests --------------------

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
    mock_interaction.response.send_message.assert_called_with(
        "Bounty Cog is not loaded or active.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_check_user_roles_success(mock_interaction, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    result = await check_user_roles(mock_interaction)
    assert result is True

@pytest.mark.asyncio
async def test_check_user_roles_failure(mock_interaction):
    mock_interaction.user.roles = []
    result = await check_user_roles(mock_interaction)
    assert result is False
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_current_bounty_success(mock_interaction, mock_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog
    await current_bounty(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "**Current Bounty:**\nTest bounty", ephemeral=True
    )

@pytest.mark.asyncio
async def test_current_bounty_no_cog(mock_interaction, mock_bot):
    mock_bot.get_cog.return_value = None
    await current_bounty(mock_interaction, mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "Bounty Cog is not loaded or active.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_update_bounty_image_success(mock_interaction, mock_bot, mock_cog, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    mock_bot.get_cog.return_value = mock_cog
    await update_bounty_image(mock_interaction, mock_bot, url="https://example.com/image.png")
    mock_cog.update_embed_url.assert_called_once()
    mock_interaction.response.send_message.assert_called_with("Image updated", ephemeral=True)

@pytest.mark.asyncio
async def test_update_bounty_image_permission_denied(mock_interaction, mock_bot, mock_cog):
    mock_interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog
    await update_bounty_image(mock_interaction, mock_bot, url="https://example.com/image.png")
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )

@pytest.mark.asyncio
async def test_update_bounty_description_success(mock_interaction, mock_bot, mock_cog, mock_admin_role):
    mock_interaction.user.roles = [mock_admin_role]
    mock_bot.get_cog.return_value = mock_cog
    await update_bounty_description(mock_interaction, "New description", mock_bot)
    mock_cog.update_embed_description.assert_called_once_with(new_desc="New description")
    mock_interaction.response.send_message.assert_called_with("Description updated", ephemeral=True)

@pytest.mark.asyncio
async def test_update_bounty_description_permission_denied(mock_interaction, mock_bot, mock_cog):
    mock_interaction.user.roles = []
    mock_bot.get_cog.return_value = mock_cog
    await update_bounty_description(mock_interaction, "New description", mock_bot)
    mock_interaction.response.send_message.assert_called_with(
        "You do not have permission to use this command.", ephemeral=True
    )
