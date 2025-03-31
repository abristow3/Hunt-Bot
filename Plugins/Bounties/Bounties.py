from discord.ext import commands, tasks
from HuntBot import HuntBot
from GDoc import GDoc
import asyncio
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
$bounty

Password: $password
""")

double_bounty_template = Template("""
$b1_bounty

Password: $b1_password

@@@ DOUBLE BOUNTY @@@

$b2_bounty

Password: $b2_password
""")


class Bounties:
    def __init__(self, discord_bot: commands.Bot, hunt_bot: HuntBot):
        self.discord_bot = discord_bot
        self.hunt_bot = hunt_bot
        self.bounty_channel_id = ""
        self.bounty_interval = ""
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

        # self.start_bounties()

    def start_up(self):
        self.get_bounty_interval()
        self.get_bounty_channel()
        self.get_single_bounties()
        self.get_double_bounties()

        self.process_bounties()

        self.configured = True

    def get_bounty_interval(self):
        self.bounty_interval = self.hunt_bot.config_map.get('BOUNTIES_PER_DAY', '')

        if self.bounty_interval == '':
            raise ConfigurationException(config_key='BOUNTIES_PER_DAY')

    def get_bounty_channel(self):
        self.bounty_channel_id = self.hunt_bot.config_map.get('BOUNTY_CHANNEL_ID', '')

        if self.bounty_channel_id == '':
            raise ConfigurationException(config_key='BOUNTY_CHANNEL_ID')

    def get_single_bounties(self):
        self.single_bounties_df = self.hunt_bot.pull_table_data(table_name=self.single_bounties_table_name)

        if self.single_bounties_df.empty:
            raise TableDataImportException(table_name=self.single_bounties_table_name)

    def get_double_bounties(self):
        self.double_bounties_df = self.hunt_bot.pull_table_data(table_name=self.double_bounties_table_name)

        if self.single_bounties_df.empty:
            raise TableDataImportException(table_name=self.double_bounties_table_name)

    def process_bounties(self):
        print("PROICESSING BOUNTIES")
        for index, row in self.single_bounties_df.iterrows():
            single_bounty = row["Task"]
            single_password = row["Password"]
            double = not pd.isna(row["Double"])

            # IF not a double return the single trmplate
            if not double:
                self.message = single_bounty_template.substitute(bounty=single_bounty, password=single_password)
            else:
                # If it is a double then grab a double
                data = self.double_bounties_df.iloc[0]
                double_bounty = data["Task"]
                double_password = data["Password"]

                self.message = double_bounty_template.substitute(b1_bounty=single_bounty, b1_password=single_password,
                                                                 b2_bounty=double_bounty,b2_password=double_password)
                self.double_bounties_df.drop(0, axis=0, inplace=True)
                self.double_bounties_df.reset_index(drop=True, inplace=True)

                print(self.message)

        # if double is true
        # grab a bounty from the double bounty list
        # Get bounty password
        # remove from list
        # inject bounty post template
        ...

    # def start_bounties(self):
    #     # @tasks.loop(hours=self.interval)
    #     @tasks.loop(seconds=self.interval)
    #     async def serve_bounty():
    #         channel = self.bot.get_channel(self.state.bounty_channel_id)
    #         await self.bot.wait_until_ready()
    #         while not self.bot.is_closed():
    #             for bounty in self.gdoc.bounties_list:
    #                 await channel.send("=== BOUNTY SERVED ===")
    #                 await channel.send(bounty)
    #                 await asyncio.sleep(5)
    #
    #     # Start the task
    #     serve_bounty.start()
