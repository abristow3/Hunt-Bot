from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
import gspread
import requests
import csv
import io


class GDoc:
    def __init__(self):
        self.config = {}
        # Load the configuration file
        self.setup()

        # Set Google Doc variables
        self.credentials = self.config.get("GOOGLE_CREDENTIALS_PATH", "")
        self.sheet_id = self.config.get("GOOGLE_SHEET_ID", "")
        self.dailies_sheet_name = self.config.get("DAILIES_SHEET_NAME", "")
        self.dailies_cell_range = self.config.get("DAILIES_CELL_RANGE", "")
        self.bounties_sheet_name = self.config.get("BOUNTIES_SHEET_NAME", "")
        self.bounties_cell_range = self.config.get("BOUNTIES_CELL_RANGE", "")

        # Build the a1 notation for the sheet names and cells (used when reading data)
        self.dailies_a1notation = self.a1notation_builder(sheet_name=self.dailies_sheet_name,
                                                          cell_range=self.dailies_cell_range)
        self.bounties_a1notation = self.a1notation_builder(sheet_name=self.bounties_sheet_name,
                                                           cell_range=self.bounties_cell_range)

        # Setup empty lists for gdoc data
        self.dailies_list = []
        self.bounties_list = []

        # Get the gdoc data
        self.get_google_sheet_data()

    def setup(self):
        with open("conf.yaml", 'r') as f:
            self.config = yaml.safe_load(f)

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1formatted = f"{sheet_name}!{cell_range}"
        return a1formatted

    @staticmethod
    def flatten_list(list_to_flatten: list) -> list:
        """
        Turns a list of lists into a single list

        :param list_to_flatten:
        :return list:
        """

        flat_list = [
            x
            for xs in list_to_flatten
            for x in xs
        ]

        return flat_list

    def get_google_sheet_data(self):
        # Load the service account credentials from the JSON file
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )

        # Build the Sheets API client
        service = build("sheets", "v4", credentials=credentials)

        # Call the Sheets API to get the data from the specified ranges
        sheet = service.spreadsheets()
        print("Trying to get sheet data")

        dailies_result = sheet.values().get(spreadsheetId=self.sheet_id, range=self.dailies_a1notation).execute()
        bounties_result = sheet.values().get(spreadsheetId=self.sheet_id, range=self.bounties_a1notation).execute()

        # Fetch the data
        self.dailies_list = dailies_result.get("values", [])

        # TODO Since this is 2D array need to make sure no to fill empty cells, or parse this into a better DS
        print(self.dailies_list)

        self.bounties_list = bounties_result.get("values", [])

        # TODO Use Pandas to keep this into a 2D array

        # print(self.dailies_list)

        # Flatten the list of lists (Google API returns data in that structure for some reason
        self.dailies_list = self.flatten_list(self.dailies_list)
        self.bounties_list = self.flatten_list(self.bounties_list)


