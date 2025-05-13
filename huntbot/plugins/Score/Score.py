from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
import pandas as pd
from string import Template
from huntbot.exceptions import TableDataImportException, ConfigurationException


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
        self.message = None
        self.configured = False

        self.setup()
        self.start_scores()

    def setup(self):
        self.get_score_channel()
        self.configured = True

    def get_score_channel(self):
        self.score_channel_id = int(self.hunt_bot.config_map.get('POINTS_CHANNEL_ID', "0"))

        if self.score_channel_id == 0:
            raise ConfigurationException(config_key='POINTS_CHANNEL_ID')

    def get_score(self):
        # use table map to find score table
        # pull data
        score_df = self.hunt_bot.pull_table_data(table_name=self.score_table_name)

        if score_df.empty:
            raise TableDataImportException(table_name=self.score_table_name)

        score_dict = pd.Series(score_df['Total Points'].values, index=score_df['Team Name']).to_dict()
        self.team1_points = score_dict.get("Team Orange", "")
        self.team2_points = score_dict.get("Team Green", "")

    def start_scores(self):
        channel = self.discord_bot.get_channel(self.score_channel_id)

        @tasks.loop(seconds=10)
        async def update_scores():
            self.get_score()
            message = (f"The current score is\n"
                       f"Team Orange: {self.team1_points}\n"
                       f"Team Green: {self.team2_points}")

            if self.message:
                await self.message.edit(content=message)
            else:
                self.message = await channel.send(message)

        update_scores.start()
