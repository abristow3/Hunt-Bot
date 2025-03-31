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
        try:
            if not cell_range:
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=sheet_name).execute()
            else:
                a1_range = self.a1notation_builder(sheet_name=sheet_name, cell_range=cell_range)
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=a1_range).execute()

            data = data.get('values', [])

            return data
        except Exception as e:
            print(e)
            print("Unable to get data from sheet")
            return []

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1format = f"{sheet_name}!{cell_range}"
        return a1format

# if __name__ == '__main__':
#     gdoc = GDoc()
#     gdoc.set_sheet_id(sheet_id="1VcBBIxejr0dg87LH4hg_hnznaAcmt8Afq8plTBmD6-k")
#     config_data = gdoc.get_data_from_sheet(sheet_name="BotConfig")
#     print(config_data)
#     tmap = gdoc.build_table_map(sheet_data=config_data)
#     pprint.pprint(tmap)