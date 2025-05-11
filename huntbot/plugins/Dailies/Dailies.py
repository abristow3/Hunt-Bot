from discord.ext import commands, tasks
from huntbot.HuntBot import HuntBot
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


single_daily_template = Template("""
@everyone $task

Password: $password
""")

double_daily_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE DAILY @@@

$b2_task

Password: $b2_password
""")


class Dailies:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.daily_channel_id = 0
        self.daily_interval = 24
        self.single_dailies_df = pd.DataFrame()
        self.double_dailies_df = pd.DataFrame()
        self.single_dailies_table_name = "Single Dailies"
        self.double_dailies_table_name = "Double Dailies"
        self.message = ""
        self.configured = False
        self.message_id = 0


        try:
            self.start_up()
        except Exception as e:
            print(e)
            print("Error loading dailies plugin configuration")

        self.start_dailies()

    def start_up(self):
        self.get_daily_channel()
        self.get_single_dailies()
        self.get_double_dailies()

        self.configured = True

    def get_daily_channel(self):
        self.daily_channel_id = int(self.hunt_bot.config_map.get('DAILY_CHANNEL_ID', "0"))

        if self.daily_channel_id == 0:
            raise ConfigurationException(config_key='DAILY_CHANNEL_ID')

    def get_single_dailies(self):
        self.single_dailies_df = self.hunt_bot.pull_table_data(table_name=self.single_dailies_table_name)

        if self.single_dailies_df.empty:
            raise TableDataImportException(table_name=self.single_dailies_table_name)

    def get_double_dailies(self):
        self.double_dailies_df = self.hunt_bot.pull_table_data(table_name=self.double_dailies_table_name)

        if self.single_dailies_df.empty:
            raise TableDataImportException(table_name=self.double_dailies_table_name)

    @staticmethod
    def yield_next_row(df):
        # Keep yielding the next index until the end of the list
        for index, row in df.iterrows():
            yield row

    def start_dailies(self):
        single_daily_generator = self.yield_next_row(df=self.single_dailies_df)
        double_daily_generator = self.yield_next_row(df=self.double_dailies_df)
        channel = self.discord_bot.get_channel(self.daily_channel_id)

        @tasks.loop(hours=self.daily_interval)
        async def serve_daily():
            await self.discord_bot.wait_until_ready()

            try:
                single_daily = next(single_daily_generator)
                single_task = single_daily["Task"]
                single_password = single_daily["Password"]
                double = not pd.isna(single_daily["Double"])

                # IF not a double return the single template
                if not double:
                    self.message = single_daily_template.substitute(task=single_task, password=single_password)
                else:
                    double_daily = next(double_daily_generator)
                    double_task = double_daily["Task"]
                    double_password = double_daily["Password"]

                    self.message = double_daily_template.substitute(b1_task=single_task,
                                                                     b1_password=single_password,
                                                                     b2_task=double_task,
                                                                     b2_password=double_password)

                # if message ID not 0, then there is an old message and we need to unpin it
                if self.message_id != 0:
                    old_message = await channel.fetch_message(self.message_id)
                    await old_message.unpin()

                # send message, capture ID in memory, pin message
                sent_message = await channel.send(self.message)
                self.message_id = sent_message.id
                await sent_message.pin()
            except StopIteration:
                # If we run out of dailies, stop the loop
                print("No more dailies left!")
                serve_daily.stop()


        # Start the task
        serve_daily.start()


