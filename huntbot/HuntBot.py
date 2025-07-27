from datetime import datetime, timedelta
import pytz
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class InvalidConfig(Exception):
    def __init__(self, message="Error reading configuration file"):
        # Call the base class constructor
        super().__init__(message)


class HuntBot:
    def __init__(self):
        self.table_map = {}
        self.sheet_name = ""
        self.sheet_data = pd.DataFrame()
        self.config_table_name = ""
        self.command_channel_name = "staff-chat"
        self.command_channel_id = ""
        self.config_map = {}
        self.start_date = ""
        self.start_time = ""
        self.configured = False
        self.started = False
        self.start_datetime = None
        self.end_datetime = None
        self.master_password = ""
        self.ended = False
        self.announcements_channel_id = 0

    def set_config_table_name(self, table_name: str):
        self.config_table_name = table_name

    def set_command_channel_id(self, channel_id: str):
        self.command_channel_id = channel_id

    def set_sheet_name(self, sheet_name: str):
        self.sheet_name = sheet_name

    def set_sheet_data(self, data):
        try:
            df = pd.DataFrame(data)
            df.iloc[0] = df.iloc[0].replace({"": None})
            self.sheet_data = df
        except Exception as e:
            logger.error(e)
            logger.error("Error creating Dataframe")
            self.sheet_data = []

    def build_table_map(self):
        logger.info("Building table map...")
        start_col = None
        end_col = None
        name = ""

        try:
            # Dynamically find the cells that fall under the merged cell table name
            for col in range(len(self.sheet_data.columns)):
                header_value = self.sheet_data.iloc[0, col]

                if header_value is not None:
                    name = header_value
                    start_col = col

                    self.table_map[name] = {"start_col": start_col}

                if header_value is None:
                    end_col = col
                    self.table_map.setdefault(name, {})['end_col'] = end_col
        except Exception as e:
            logger.error(e)
            logger.error("Error building table map")
            self.table_map = {}

    def pull_table_data(self, table_name: str):
        # Find table name in table map
        logger.ifo("Pulling Table Data...")
        table_metadata = self.table_map.get(table_name, {})
        if not table_metadata:
            return []

        logger.info(f"Data located between columns {table_metadata['start_col']} and {table_metadata['end_col']}")

        # get the data based on the start and end columns
        df = self.sheet_data.loc[:, table_metadata['start_col']:table_metadata['end_col']]

        # Clean the data
        # Drop the first row (table name)
        df.drop(0, axis=0, inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Drop the empty columns
        df.replace("", pd.NA, inplace=True)
        df_cleaned_col = df.dropna(axis=1, how='all')

        # Drop the empty rows
        df_cleaned = df_cleaned_col.dropna(how='all')

        # Set column names from table headers (row 1)
        df_cleaned.columns = df_cleaned.iloc[0]
        df_cleaned = df_cleaned.drop(0).reset_index(drop=True)

        return df_cleaned

    def load_config(self, df):
        # Turn config DF into dict
        self.config_map = dict(zip(df['Key'], df['Value']))

        if not self.config_map:
            logger.error("Error loading discord config data")

        self.start_date = self.config_map.get("HUNT_START_DATE", "")
        self.start_time = self.config_map.get("HUNT_START_TIME_GMT", "")
        self.master_password = self.config_map.get("MASTER_PASSWORD", "")
        self.announcements_channel_id = int(self.config_map.get('ANNOUNCEMENTS_CHANNEL_ID', "0"))

        if self.announcements_channel_id == 0:
            logger.error("Error loading announcement channel ID date")
        elif self.start_date == "":
            logger.error("Error loading hunt start date")
        elif self.start_time == "":
            logger.error("Error loading hunt start time")
        elif self.master_password == "":
            logger.error("Error loading master password")

        # Combine the date and time strings
        start_datetime_str = f"{self.start_date} {self.start_time}"

        # Convert to datetime object
        self.start_datetime = datetime.strptime(start_datetime_str, "%d/%m/%Y %H:%M")
        self.start_datetime = pytz.timezone('Europe/London').localize(self.start_datetime)
        self.end_datetime = self.start_datetime + timedelta(days=9)

        self.configured = True

    @staticmethod
    def get_current_gmt_time():
        # Convert local time to GMT
        gmt_timezone = pytz.timezone('Europe/London')
        gmt_time = datetime.now(gmt_timezone)
        return gmt_time

    def check_start(self):
        ctime = self.get_current_gmt_time()

        logger.info(f"Current time is: {ctime}, Hunt Start Date time is: {self.start_datetime}")

        if ctime < self.start_datetime:
            return
        else:
            self.started = True

    def check_end(self):
        ctime = self.get_current_gmt_time()

        logger.info(f"Current time is: {ctime}, Hunt End date time is: {self.end_datetime}")

        if ctime >= self.end_datetime:
            self.ended = True
        else:
            return
