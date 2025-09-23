import pytest
from unittest.mock import AsyncMock, MagicMock
from huntbot.commands.bounties_command import complete_bounty, fetch_cog, current_bounty, update_bounty_image, update_bounty_description, check_user_roles
import discord
from unittest.mock import AsyncMock, MagicMock
from huntbot.HuntBot import HuntBot


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
def mock_hunt_bot():
    bot = MagicMock(spec=HuntBot)
    bot.team_one_name = "Red"
    bot.team_two_name = "Blue"
    return bot

@pytest.fixture
def mock_cog():
    cog = AsyncMock()
    cog.bounty_description = "@everyone Test bounty"
    cog.update_embed_url.return_value = "Image updated"
    cog.update_embed_description.return_value = "Description updated"
    cog.first_place = ""
    cog.second_place = ""
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

@pytest.mark.asyncio
async def test_complete_bounty_first_place(mock_interaction, mock_bot, mock_hunt_bot, mock_cog):
    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock()
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_bounty(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        hunt_bot=mock_hunt_bot,
        team_color="Red"
    )

    assert mock_cog.first_place == "Red"
    mock_cog.post_bounty_complete_message.assert_awaited_with(team_name="Red", placement="First")
    mock_interaction.response.send_message.assert_called_with(
        "First place completion message posted succesfully for Red", ephemeral=True
    )


@pytest.mark.asyncio
async def test_complete_bounty_second_place(mock_interaction, mock_bot, mock_hunt_bot, mock_cog):
    # Setup: first place already claimed
    mock_cog.first_place = "Red"
    mock_cog.second_place = ""  # Ensure it's empty to allow second place

    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock()
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_bounty(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        hunt_bot=mock_hunt_bot,
        team_color="Blue"
    )

    # Verify second place is set
    assert mock_cog.second_place == "Blue"

    # Check the correct message was sent to channel
    mock_cog.post_bounty_complete_message.assert_awaited_with(team_name="Blue", placement="Second")
    mock_interaction.response.send_message.assert_called_with(
        "Second place completion message posted succesfully for Blue", ephemeral=True
    )

@pytest.mark.asyncio
async def test_complete_bounty_already_claimed(mock_interaction, mock_bot, mock_hunt_bot, mock_cog):
    # Setup: both first and second place are already claimed
    mock_cog.first_place = "Red"
    mock_cog.second_place = "Blue"

    mock_bot.get_cog.return_value = mock_cog

    role = MagicMock()
    role.name = "staff"
    mock_interaction.user.roles = [role]

    await complete_bounty(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        hunt_bot=mock_hunt_bot,
        team_color="Green"
    )

    # Ensure no update to cog
    assert mock_cog.first_place == "Red"
    assert mock_cog.second_place == "Blue"

    # It should NOT call the post method
    mock_cog.post_bounty_complete_message.assert_not_awaited()

    # It should respond with the already-claimed message
    mock_interaction.response.send_message.assert_called_with(
        "First and Second place already claimed for the bounty", ephemeral=True
    )
