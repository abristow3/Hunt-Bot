import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from huntbot.commands.dailies_command import complete_daily, fetch_cog, check_user_roles, current_daily, update_daily_image, update_daily_description
from huntbot.HuntBot import HuntBot

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.user.roles = [MagicMock(name='admin', spec=['name'])]
    interaction.user.roles[0].name = "Admin"
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
    cog.daily_description = "@everyone Test daily"
    cog.update_embed_url.return_value = "Image updated"
    cog.update_embed_description.return_value = "Description updated"
    cog.first_place = ""
    cog.second_place = ""
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
    result = await check_user_roles(mock_interaction, authorized_roles=["admin"])
    assert result is True


@pytest.mark.asyncio
async def test_check_user_roles_unauthorized():
    interaction = AsyncMock()
    interaction.user.roles = []
    result = await check_user_roles(interaction, authorized_roles=["admin"])
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

@pytest.mark.asyncio
async def test_complete_daily_first_place(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    # Setup
    mock_bot.get_cog.return_value = mock_cog
    mock_interaction.user.roles = [MagicMock(name="staff", spec=["name"])]
    mock_interaction.user.roles[0].name = "staff"

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Red",
        hunt_bot=mock_hunt_bot
    )

    # Verify first_place set
    assert mock_cog.first_place == "Red"
    mock_cog.post_daily_complete_message.assert_awaited_with(team_name="Red", placement="First")
    mock_interaction.response.send_message.assert_called_with(
        "First place completion message posted succesfully for Red", ephemeral=True
    )

@pytest.mark.asyncio
async def test_complete_daily_second_place(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    # Setup: first place already taken
    mock_cog.first_place = "Red"
    mock_cog.second_place = ""  # Ensure second is open

    mock_bot.get_cog.return_value = mock_cog
    mock_interaction.user.roles = [MagicMock(name="staff", spec=["name"])]
    mock_interaction.user.roles[0].name = "staff"

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Blue",
        hunt_bot=mock_hunt_bot
    )

    # Verify second_place set
    assert mock_cog.second_place == "Blue"
    mock_cog.post_daily_complete_message.assert_awaited_with(team_name="Blue", placement="Second")
    mock_interaction.response.send_message.assert_called_with(
        "Second place completion message posted succesfully for Blue", ephemeral=True
    )

@pytest.mark.asyncio
async def test_complete_daily_already_claimed(mock_interaction, mock_bot, mock_cog, mock_hunt_bot):
    # Setup: both places claimed
    mock_cog.first_place = "Red"
    mock_cog.second_place = "Blue"

    mock_bot.get_cog.return_value = mock_cog
    mock_interaction.user.roles = [MagicMock(name="staff", spec=["name"])]
    mock_interaction.user.roles[0].name = "staff"

    await complete_daily(
        interaction=mock_interaction,
        discord_bot=mock_bot,
        team_color="Green",
        hunt_bot=mock_hunt_bot
    )

    # Verify nothing updated and error sent
    mock_cog.post_daily_complete_message.assert_not_awaited()
    mock_interaction.response.send_message.assert_called_with(
        "First and Second place already claimed for the daily", ephemeral=True
    )
