from discord.ext import commands, tasks
from HuntBot import HuntBot
import pandas as pd
from string import Template


class TableDataImportException(Exception):
    def __init__(self, message="Configuration error occurred", table_name=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic config key
        self.config_key = table_name

    def __str__(self):
        # Customize the string representation of the exception
        if self.config_key:
            return f'{self.args[0]} (Config key: {self.config_key})'
        return self.args[0]


class ConfigurationException(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message="Configuration error occurred", config_key=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic config key
        self.config_key = config_key

    def __str__(self):
        # Customize the string representation of the exception
        if self.config_key:
            return f'{self.args[0]} (Config key: {self.config_key})'
        return self.args[0]


score_message = Template("""
The current score is $team1_name: $team1_points $team2_name: $team2_points
""")


class Score:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.score_channel_id = 0
        self.team1_points = 0
        self.team2_points = 0
        self.score_table_name = "Current Score"

    def get_score_channel(self):
        self.score_channel_id = int(self.hunt_bot.config_map.get('SCORE_CHANNEL_ID', "0"))

        if self.score_channel_id == 0:
            raise ConfigurationException(config_key='SCORE_CHANNEL_ID')

    def get_score(self):
        # use table map to find score table
        # pull data
        score_df = self.hunt_bot.pull_table_data(table_name=self.score_table_name)

        print(score_df)

        if score_df.empty:
            raise TableDataImportException(table_name=self.score_table_name)
