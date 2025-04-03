from datetime import timedelta, datetime
from string import Template
import math
import pytz
from discord.ext import commands, tasks
from HuntBot import HuntBot

begins_template = Template("""
The Hunt begins in $num_hours hours!
""")

ends_template = Template("""
The Hunt ends in $num_hours hours!
""")

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

class Countdown:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        # Todo as we publish the message, divide these by 2
        self.countdown_interval = 24  # This interval i will be havled everytime a message is posted, then reset after it hits '1' back to 24
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.announcements_channel_id = 0
        # Set the announcement plugin start time to 24 hours prior to the hunt start datetime
        # self.countdown_start_date = self.hunt_bot.start_datetime - timedelta(days=1)
        london_tz = pytz.timezone('Europe/London')

        self.countdown_start_date =london_tz.localize(datetime(2025, 4, 3, 12, 0, 0))
        self.countdown_end_date = self.countdown_start_date + timedelta(days=10)

        self.start_completed = False
        self.end_completed = False
        self.start = False
        self.end = False
        self.message = ""
        # Flag to ensure the countdown starts only once
        self.countdown_task_started = False
        self.setup()

    def setup(self):
        self.announcements_channel_id = int(self.hunt_bot.config_map.get('ANNOUNCEMENTS_CHANNEL_ID', "0"))
        if self.announcements_channel_id == 0:
            raise ConfigurationException(config_key='ANNOUNCEMENTS_CHANNEL_ID')

    @staticmethod
    def get_current_gmt_time():
        # Convert local time to GMT
        gmt_timezone = pytz.timezone('Europe/London')
        gmt_time = datetime.now(gmt_timezone)
        return gmt_time

    def check_time(self):
        ctime = self.get_current_gmt_time()
        return ctime

    def update_interval(self):
        if self.countdown_interval > 1:
            self.countdown_interval = math.floor(self.countdown_interval / 2)
        elif self.countdown_interval <= 1 and self.start_completed:
            self.end_completed = True
            self.end = False
        elif self.countdown_interval <= 1:
            self.start_completed = True
            self.start = False
            # Reset to 24
            self.countdown_interval = 24

    def start_countdown(self):
        if self.countdown_task_started:
            return  # Don't start the loop again

        self.countdown_task_started = True
        channel = self.discord_bot.get_channel(self.announcements_channel_id)

        @tasks.loop(seconds=5)
        async def begin_countdown():
            await self.discord_bot.wait_until_ready()

            ctime = self.check_time()

            if self.hunt_bot.started:
                self.start = False
            elif not self.start_completed and ctime >= self.countdown_start_date:
                self.start = True
            elif not self.end_completed and ctime >= self.countdown_end_date:
                self.end = True

            if self.end:
                self.message = ends_template.substitute(num_hours=self.countdown_interval)
                await channel.send(self.message)
                self.update_interval()
            elif self.start:
                self.message = begins_template.substitute(num_hours=self.countdown_interval)
                await channel.send(self.message)
                self.update_interval()
            else:
                print("Not time to start yet")
                return

        begin_countdown.start()
