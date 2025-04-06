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


single_bounty_template = Template("""
@everyone $task

Password: $password
""")

double_bounty_template = Template("""
@everyone $b1_task

Password: $b1_password

@@@ DOUBLE BOUNTY @@@

$b2_task

Password: $b2_password
""")


class Bounties:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.bounties_per_day = 0
        self.bounty_channel_id = 0
        self.bounty_interval = 0
        self.single_bounties_df = pd.DataFrame()
        self.double_bounties_df = pd.DataFrame()
        self.single_bounties_table_name = "Single Bounties"
        self.double_bounties_table_name = "Double Bounties"
        self.message = ""
        self.configured = False

        try:
            self.start_up()
        except Exception as e:
            print(e)
            print("Error loading Bounties plugin configuration")

        self.start_bounties()

    def start_up(self):
        self.get_bounties_per_day()
        self.set_bounty_interval()
        self.get_bounty_channel()
        self.get_single_bounties()
        self.get_double_bounties()

        self.configured = True

    def get_bounties_per_day(self):
        self.bounties_per_day = int(self.hunt_bot.config_map.get('BOUNTIES_PER_DAY', "0"))

        if self.bounties_per_day == 0:
            raise ConfigurationException(config_key='BOUNTIES_PER_DAY')

    def set_bounty_interval(self):
        self.bounty_interval = 24/self.bounties_per_day

    def get_bounty_channel(self):
        self.bounty_channel_id = int(self.hunt_bot.config_map.get('BOUNTY_CHANNEL_ID', "0"))

        if self.bounty_channel_id == 0:
            raise ConfigurationException(config_key='BOUNTY_CHANNEL_ID')

    def get_single_bounties(self):
        self.single_bounties_df = self.hunt_bot.pull_table_data(table_name=self.single_bounties_table_name)

        if self.single_bounties_df.empty:
            raise TableDataImportException(table_name=self.single_bounties_table_name)

    def get_double_bounties(self):
        self.double_bounties_df = self.hunt_bot.pull_table_data(table_name=self.double_bounties_table_name)

        if self.single_bounties_df.empty:
            raise TableDataImportException(table_name=self.double_bounties_table_name)

    @staticmethod
    def yield_next_row(df):
        # Keep yielding the next index until the end of the list
        for index, row in df.iterrows():
            yield row

    def start_bounties(self):
        single_bounty_generator = self.yield_next_row(df=self.single_bounties_df)
        double_bounty_generator = self.yield_next_row(df=self.double_bounties_df)
        channel = self.discord_bot.get_channel(self.bounty_channel_id)

        @tasks.loop(hours=self.bounty_interval)
        async def serve_bounty():
            await self.discord_bot.wait_until_ready()

            try:
                single_bounty = next(single_bounty_generator)
                single_task = single_bounty["Task"]
                single_password = single_bounty["Password"]
                double = not pd.isna(single_bounty["Double"])

                # IF not a double return the single template
                if not double:
                    self.message = single_bounty_template.substitute(task=single_task, password=single_password)
                else:
                    double_bounty = next(double_bounty_generator)
                    double_task = double_bounty["Task"]
                    double_password = double_bounty["Password"]

                    self.message = double_bounty_template.substitute(b1_task=single_task,
                                                                     b1_password=single_password,
                                                                     b2_task=double_task,
                                                                     b2_password=double_password)
                await channel.send(self.message)
            except StopIteration:
                # If we run out of bounties, stop the loop
                print("No more bounties left!")
                serve_bounty.stop()


        # Start the task
        serve_bounty.start()
