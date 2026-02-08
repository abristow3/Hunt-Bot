import pytest
from unittest.mock import MagicMock
from huntbot.HuntBot import HuntBot


@pytest.fixture
def hunt_bot():
    return HuntBot()


def test_generate_participant_whitelist_populates_set(monkeypatch, hunt_bot):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "participations": [
            {"player": {"displayName": "Alice"}},
            {"player": {"displayName": "Bob"}},
            {"player": {}},  # missing displayName
            {},  # missing player
            {"player": {"displayName": ""}},  # empty name
        ]
    }

    def mock_get(url):
        return mock_response

    monkeypatch.setattr("huntbot.HuntBot.requests.get", mock_get)

    hunt_bot.generate_participant_whitelist()

    assert sorted(hunt_bot.participant_whitelist) == ["Alice", "Bob"]


def test_generate_participant_whitelist_empty_response(monkeypatch, hunt_bot):
    mock_response = MagicMock()
    mock_response.json.return_value = {"participations": []}

    monkeypatch.setattr(
        "huntbot.HuntBot.requests.get",
        lambda url: mock_response
    )

    hunt_bot.generate_participant_whitelist()

    assert hunt_bot.participant_whitelist == set()


def test_print_whitelist_outputs_sorted_list(monkeypatch, hunt_bot):
    hunt_bot.participant_whitelist = {"Bob", "Alice"}

    mock_print = MagicMock()
    monkeypatch.setattr("builtins.print", mock_print)

    hunt_bot.print_whitelist()

    mock_print.assert_called_once_with(["Alice", "Bob"])


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
