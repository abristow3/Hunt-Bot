import yaml
import pandas


class InvalidConfig(Exception):
    def __init__(self, message="Error reading configuration file"):
        # Call the base class constructor
        super().__init__(message)


class HuntBot:
    def __init__(self):
        self.config_map = {}
        self.configured = False
        self.config_sheet_name = "BotConfig"
        self.config_cell_range = "A3:B12"

    def setup_config(self, config_map: dict):
        # Check config_map is populated
        if config_map:
            self.config_map = config_map

        # Find the Config Table


            self.configured = True


        # Load config
        # with open('conf.yaml', 'r') as f:
        #     data = yaml.safe_load(f)
        #
        # # Set Constants
        # self.discord_token = data.get("DISCORD_TOKEN", "")
        # self.bounty_channel_id = data.get("BOUNTY_CHANNEL_ID", "")
        # self.daily_channel_id = data.get("DAILY_CHANNEL_ID", "")
        # self.staff_channel_id = data.get("STAFF_CHANNEL_ID", "")
        # self.start_time = data.get("HUNT_START_TIME_GMT", "16:00")
        # self.bounties_per_day = data.get('BOUNTIES_PER_DAY', 4)
        # self.bounty_tick = 24 / self.bounties_per_day
        #
        # if self.discord_token == "":
        #     print("No Discord token found in configuration file.")
        #     raise InvalidConfig
        #
        # if self.bounties_per_day == "":
        #     print("Bounties per day not configured")
        #     raise InvalidConfig
        #
        # if self.bounty_channel_id == "":
        #     print("Bounty Channel ID missing")
        #     raise InvalidConfig
        #
        # if self.daily_channel_id == "":
        #     print("Daily Channel ID missing")
        #     raise InvalidConfig
        #
        # if self.staff_channel_id == "":
        #     print("Staff Channel ID missing")
        #     raise InvalidConfig
