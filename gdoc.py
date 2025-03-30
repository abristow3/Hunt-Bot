from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
import requests
import csv
import io


class GDoc:
    def __init__(self):
        self.config = {}
        self.sheets = None
        self.config_sheet = None

        with open("conf.yaml", 'r') as f:
            self.config = yaml.safe_load(f)

        self.sheet_id = ""

        # Load the service account credentials from the JSON file
        self.creds_path = self.config.get("GOOGLE_CREDENTIALS_PATH", "")
        self.credentials = service_account.Credentials.from_service_account_file(self.creds_path, scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly"], )
        self.service = None
        try:
            self.service = build("sheets", "v4", credentials=self.credentials)
        except Exception:
            print(Exception)

    def set_sheet_id(self,sheet_id:str):
        self.sheet_id=sheet_id

    def pull_sheets(self):
        # Build the Sheets API client
        self.sheets = self.service.spreadsheets()

    def get_sheet(self, sheet_name: str):
        sheet = self.sheets.values().get(spreadsheetId=self.sheet_id, range=sheet_name).execute()
        return sheet


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
    # @staticmethod
    # def a1notation_builder(sheet_name: str, cell_range: str) -> str:
    #     a1formatted = f"{sheet_name}!{cell_range}"
    #     return a1formatted
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

    #     print("Trying to get sheet data")
    #
    #     dailies_result = sheet.values().get(spreadsheetId=self.sheet_id, range=self.dailies_a1notation).execute()
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
