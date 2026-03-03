import pytest
from huntbot.HuntBot import HuntBot


@pytest.fixture
def hunt_bot():
    return HuntBot()


def test_generate_wom_competition_urls_appends_id(hunt_bot):
    hunt_bot.wom_competition_id = 12345
    hunt_bot.generate_wom_competition_urls()

    assert hunt_bot.wom_event_api_url.endswith("12345")
    assert hunt_bot.wom_event_website_url.endswith("12345")


def test_generate_wom_competition_urls_with_zero_id(hunt_bot):
    hunt_bot.wom_competition_id = 0
    hunt_bot.generate_wom_competition_urls()

    assert hunt_bot.wom_event_api_url.endswith("0")
    assert hunt_bot.wom_event_website_url.endswith("0")
