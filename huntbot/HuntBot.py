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
        self.command_channel_id = 0
        self.config_map = {}
        self.start_date = ""
        self.start_time = ""
        self.configured = False
        self.started = False
        self.start_datetime = None
        self.end_datetime = None
        self.master_password = ""
        self.bounty_password = ""
        self.daily_password = ""
        self.ended = False
        self.announcements_channel_id = 0
        self.team_one_name = ""
        self.team_two_name = ""
        self.team_one_chat_channel_id = 0
        self.team_two_chat_channel_id = 0
        self.hunt_edition = ""
        self.wom_hunt_url = ""
        self.guild_id = 699971574689955850

        # TODO hardcode these for now
        self.general_channel_id = 699971574689955853
        self.admin_channel_id = 0


    def set_config_table_name(self, table_name: str):
        self.config_table_name = table_name

    def set_command_channel_id(self, channel_id: int):
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
            self.sheet_data = pd.DataFrame()

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
        logger.info("Pulling Table Data...")
        table_metadata = self.table_map.get(table_name, {})
        if not table_metadata:
            return []

        logger.info(f"Data located between columns {table_metadata['start_col']} and {table_metadata['end_col']}")

        # Get the data between columns
        df = self.sheet_data.iloc[:, table_metadata['start_col']:table_metadata['end_col'] + 1].copy()

        # Drop the header row (merged cell label)
        df = df.drop(index=0).reset_index(drop=True)

        # Replace empty strings with pd.NA
        df = df.replace("", pd.NA)

        # Drop completely empty columns
        df = df.dropna(axis=1, how='all')

        # Drop completely empty rows
        df = df.dropna(how='all')

        # Set the second row (index 0 now) as column headers
        df.columns = df.iloc[0]
        df = df.drop(index=0).reset_index(drop=True)

        return df

    def load_config(self, df):
        try:
            # Turn config DF into dict
            self.config_map = dict(zip(df['Key'], df['Value']))
        except Exception as e:
            logger.exception("Failed to parse configuration dataframe.")
            raise InvalidConfig("Failed to parse configuration dataframe.")

        if not self.config_map:
            raise InvalidConfig("Configuration map is empty.")

        try:
            self.start_date = self.config_map.get("HUNT_START_DATE", "")
            self.start_time = self.config_map.get("HUNT_START_TIME_GMT", "")
            self.master_password = self.config_map.get("MASTER_PASSWORD", "")
            self.announcements_channel_id = int(self.config_map.get('ANNOUNCEMENTS_CHANNEL_ID', "0"))
            self.general_channel_id = int(self.config_map.get('GENERAL_CHANNEL_ID', "0"))
            self.admin_channel_id = int(self.config_map.get("ADMIN_CHANNEL_ID", "0"))
            self.team_one_name = self.config_map.get("TEAM_ONE_NAME", "")
            self.team_two_name = self.config_map.get("TEAM_TWO_NAME", "")
            self.team_one_chat_channel_id = int(self.config_map.get("TEAM_1_CHAT_CHANNEL_ID", "0"))
            self.team_two_chat_channel_id = int(self.config_map.get("TEAM_2_CHAT_CHANNEL_ID", "0"))
            self.hunt_edition = self.config_map.get("HUNT_EDITION", "")
            self.wom_hunt_url = self.config_map.get("WOM_HUNT_URL", "")
        except ValueError as e:
            logger.exception("Invalid type in config values (expected integer for channel IDs).", exc_info=e)
            raise InvalidConfig("Invalid type in config values: expected integers for channel IDs.")

        missing_fields = []

        if self.announcements_channel_id == 0:
            missing_fields.append("ANNOUNCEMENTS_CHANNEL_ID")
        if self.general_channel_id == 0:
            missing_fields.append("GENERAL_CHANNEL_ID")
        if self.admin_channel_id == 0:
            missing_fields.append("ADMIN_CHANNEL_ID")
        if not self.start_date:
            missing_fields.append("HUNT_START_DATE")
        if not self.start_time:
            missing_fields.append("HUNT_START_TIME_GMT")
        if not self.master_password:
            missing_fields.append("MASTER_PASSWORD")
        if not self.team_one_name:
            missing_fields.append("TEAM_ONE_NAME")
        if not self.team_two_name:
            missing_fields.append("TEAM_TWO_NAME")
        if self.team_one_chat_channel_id == 0:
            missing_fields.append("TEAM_1_CHAT_CHANNEL_ID")
        if self.team_two_chat_channel_id == 0:
            missing_fields.append("TEAM_2_CHAT_CHANNEL_ID")
        if not self.hunt_edition:
            missing_fields.append("HUNT_EDITION")
        if not self.wom_hunt_url:
            missing_fields.append("WOM_HUNT_URL")

        if missing_fields:
            logger.error(f"Missing or invalid configuration fields: {', '.join(missing_fields)}")
            raise InvalidConfig(f"Missing or invalid configuration fields: {', '.join(missing_fields)}")

        # Combine the date and time strings
        start_datetime_str = f"{self.start_date} {self.start_time}"

        try:
            self.start_datetime = datetime.strptime(start_datetime_str, "%d/%m/%Y %H:%M")
            self.start_datetime = pytz.timezone('Europe/London').localize(self.start_datetime)
        except ValueError:
            logger.exception(f"Invalid date/time format: {start_datetime_str}")
            raise InvalidConfig("Invalid date/time format. Expected format: DD/MM/YYYY HH:MM")

        self.end_datetime = self.start_datetime + timedelta(days=9)
        self.configured = True
        self.update_config_for_state()

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
            self.update_config_for_state()

    def check_end(self):
        ctime = self.get_current_gmt_time()

        logger.info(f"Current time is: {ctime}, Hunt End date time is: {self.end_datetime}")

        if ctime >= self.end_datetime:
            self.ended = True
            self.update_config_for_state()
        else:
            return

    def update_config_for_state(self):
        self.config_map['COMMAND_CHANNEL_ID'] = self.command_channel_id
        self.config_map['CONFIGURED'] = self.configured
        self.config_map['STARTED'] = self.started
        self.config_map['END_DATETIME'] = self.end_datetime
        self.config_map['BOUNTY_PASSWORD'] = self.bounty_password
        self.config_map['DAILY_PASSWORD'] = self.daily_password
        self.config_map['ENDED'] = self.ended
