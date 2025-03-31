from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
import requests
import csv
import io
import pandas as pd
from tabulate import tabulate
import pprint


class GDoc:
    def __init__(self):
        self.service = None
        self.sheets = None
        self.sheet_id = ""
        self.creds_path = ""
        self.credentials = ""
        self.tables = {}
        self.on_startup()

    def on_startup(self):
        try:
            with open("conf.yaml", 'r') as f:
                config = yaml.safe_load(f)
            # Load the service account credentials from the JSON file
            self.creds_path = config.get("GOOGLE_CREDENTIALS_PATH", "")
            print(f"CREDPATH {self.creds_path}")

            self.credentials = service_account.Credentials.from_service_account_file(self.creds_path, scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly"], )

            # Build the Sheets API client
            self.service = build("sheets", "v4", credentials=self.credentials)
            self.sheets = self.service.spreadsheets()
        except Exception as e:
            print(e)

    def set_sheet_id(self, sheet_id: str):
        self.sheet_id = sheet_id

    def get_data_from_sheet(self, sheet_name: str, cell_range: str = None):
        if not cell_range:
            data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=sheet_name).execute()
        else:
            a1_range = self.a1notation_builder(sheet_name=sheet_name, cell_range=cell_range)
            data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=a1_range).execute()

        data = data.get('values', {})

        return data

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1format = f"{sheet_name}!{cell_range}"
        return a1format

    def build_tables(self):
        data = gdoc.get_data_from_sheet(sheet_name="BotConfig")
        df = pd.DataFrame(data)
        df.iloc[0] = df.iloc[0].replace({"": None})

        start_col = None
        end_col = None
        name = ""
        # Dynamically find the cells that fall under the merged cell table name
        for col in range(len(df.columns)):
            header_value = df.iloc[0, col]

            if header_value is not None:
                name = header_value
                start_col = col

                self.tables[name] = {"start_col": start_col}

            if header_value is None:
                end_col = col
                self.tables.setdefault(name, {})['end_col'] = end_col


if __name__ == '__main__':
    gdoc = GDoc()
    gdoc.set_sheet_id(sheet_id="1VcBBIxejr0dg87LH4hg_hnznaAcmt8Afq8plTBmD6-k")
    config_data = gdoc.get_data_from_sheet(sheet_name="BotConfig")
    gdoc.build_tables()
    pprint.pprint(gdoc.tables)

    #
    #     # Set Google Doc variables
    #     self.credentials = self.config.get("GOOGLE_CREDENTIALS_PATH", "")
    #     self.sheet_id = self.config.get("GOOGLE_SHEET_ID", "")
    #     self.dailies_sheet_name = self.config.get("DAILIES_SHEET_NAME", "")
    #     self.dailies_cell_range = self.config.get("DAILIES_CELL_RANGE", "")
    #     self.bounties_sheet_name = self.config.get("BOUNTIES_SHEET_NAME", "")
    #     self.bounties_cell_range = self.config.get("BOUNTIES_CELL_RANGE", "")
    #
    #     # Build the a1 notation for the sheet names and cells (used when reading data)
    #     self.dailies_a1notation = self.a1notation_builder(sheet_name=self.dailies_sheet_name,
    #                                                       cell_range=self.dailies_cell_range)
    #     self.bounties_a1notation = self.a1notation_builder(sheet_name=self.bounties_sheet_name,
    #                                                        cell_range=self.bounties_cell_range)
    #
    #     # Setup empty lists for gdoc data
    #     self.dailies_list = []
    #     self.bounties_list = []
    #
    #     # Get the gdoc data
    #     self.get_google_sheet_data()
    #

    #

    #
    # @staticmethod
    # def flatten_list(list_to_flatten: list) -> list:
    #     """
    #     Turns a list of lists into a single list
    #
    #     :param list_to_flatten:
    #     :return list:
    #     """
    #
    #     flat_list = [
    #         x
    #         for xs in list_to_flatten
    #         for x in xs
    #     ]
    #
    #     return flat_list
    #
    # def get_google_sheet_data(self):

    #     bounties_result = sheet.values().get(spreadsheetId=self.sheet_id, range=self.bounties_a1notation).execute()
    #
    #     # Fetch the data
    #     self.dailies_list = dailies_result.get("values", [])
    #
    #     # TODO Since this is 2D array need to make sure no to fill empty cells, or parse this into a better DS
    #     print(self.dailies_list)
    #
    #     self.bounties_list = bounties_result.get("values", [])
    #
    #     # TODO Use Pandas to keep this into a 2D array
    #
    #     # print(self.dailies_list)
    #
    #     # Flatten the list of lists (Google API returns data in that structure for some reason
    #     self.dailies_list = self.flatten_list(self.dailies_list)
    #     self.bounties_list = self.flatten_list(self.bounties_list)
    #
    #
