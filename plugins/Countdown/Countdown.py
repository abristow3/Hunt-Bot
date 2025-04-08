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
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.announcements_channel_id = 0
        # Set the announcement plugin start time to 24 hours prior to the hunt start datetime
        # self.countdown_start_date = self.hunt_bot.start_datetime - timedelta(days=1)
        london_tz = pytz.timezone('Europe/London')

        self.countdown_start_date = london_tz.localize(datetime(2025, 4, 3, 12, 0, 0))
        self.countdown_end_date = self.countdown_start_date + timedelta(days=9)

        self.start_completed = False
        self.end_completed = False
        self.start = False
        self.end = False
        self.message = ""
        # Flag to ensure the countdown starts only once
        self.countdown_task_started = False
        self.countdown_intervals = [24, 12, 6, 2, 1]
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

    def start_countdown(self):
        if self.countdown_task_started:
            return  # Don't start the loop again

        self.countdown_task_started = True
        channel = self.discord_bot.get_channel(self.announcements_channel_id)


        @tasks.loop(seconds=5)
        async def begin_countdown():
            print("checking countdown")
            await self.discord_bot.wait_until_ready()

            ctime = self.check_time()

            # Calculate remaining time until the start and the end of the event
            remaining_time_start = self.countdown_start_date - ctime
            print(f"remaining tiem start: {remaining_time_start}")
            remaining_hours_start = remaining_time_start.total_seconds() / 3600  # Convert to hours

            remaining_time_end = self.countdown_end_date - ctime
            print(f"remaining tiem end: {remaining_time_end}")
            remaining_hours_end = remaining_time_end.total_seconds() / 3600  # Convert to hours

            # Round the remaining hours to the nearest whole number
            remaining_hours_start = round(remaining_hours_start)
            remaining_hours_end = round(remaining_hours_end)

            print(f"TIME TILL START: {remaining_hours_start}")
            print(f"TIME TILL END: {remaining_hours_end}")

            # Check if remaining time is within the specified intervals for the start time
            if not self.start_completed and remaining_hours_start in self.countdown_intervals:
                self.message = begins_template.substitute(num_hours=remaining_hours_start)
                await channel.send(self.message)
                self.countdown_intervals.remove(remaining_hours_start)  # Remove the interval to prevent re-sending

            # If all start intervals are sent, reset countdown intervals for end time
            if not self.start_completed and not self.countdown_intervals:
                self.start_completed = True
                self.countdown_intervals = [24, 12, 6, 2, 1]  # Reset intervals for the end time

            # If start time is complete, start sending end time countdown messages
            if self.start_completed and not self.end_completed:
                # Check if remaining time is within the specified intervals for the end time
                if remaining_hours_end in self.countdown_intervals:
                    self.message = ends_template.substitute(num_hours=remaining_hours_end)
                    await channel.send(self.message)
                    self.countdown_intervals.remove(remaining_hours_end)  # Remove the interval to prevent re-sending

                # If all end intervals are sent, mark the end as completed
                if not self.countdown_intervals:
                    self.end_completed = True

            # If the event has started, no more messages will be sent for start
            if not self.start_completed and ctime >= self.countdown_start_date:
                self.start_completed = True

            # If the event has ended, no more messages will be sent for end
            if not self.end_completed and ctime >= self.countdown_end_date:
                self.end_completed = True

        begin_countdown.start()
