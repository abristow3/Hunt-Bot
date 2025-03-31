import yaml
import pandas as pd


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
        self.command_channel_name = "staff"
        self.command_channel_id = ""

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
            print(e)
            print("Error creating Dataframe")
            self.sheet_data = []

    def build_table_map(self):
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
            print(e)
            print("Error building table map")
            self.table_map = {}

    def pull_table_data(self, table_name: str):
        # Find table name in table map
        table_metadata = self.table_map.get(table_name, {})

        if not table_metadata:
            return []

        # TODO
        # we found the table in our map
        # get the data based on the start and end columns
