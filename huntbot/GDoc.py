from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
import os


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
            config_paths = ["conf/conf.yaml", "../conf/conf.yaml"]
            config = None
            
            for path in config_paths:
                try:
                    with open(path, 'r') as f:
                        config = yaml.safe_load(f)
                    print(f"Loaded configuration from {path}")
                    break
                except FileNotFoundError:
                    continue
            
            if not config:
                print("Could not find configuration file in any of the expected locations")
                return
            
            # Load the service account credentials from the JSON file
            self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

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
