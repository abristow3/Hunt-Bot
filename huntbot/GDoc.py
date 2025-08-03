from googleapiclient.discovery import build
from google.oauth2 import service_account
import yaml
import os
import logging

logger = logging.getLogger(__name__)

class GDoc:
    def __init__(self) -> None:
        self.service = None
        self.sheets = None
        self.sheet_id = ""
        self.creds_path = ""
        self.credentials = ""
        self.on_startup()

    def on_startup(self) -> None:
        try:
            with open("conf/conf.yaml", 'r') as f:
                config = yaml.safe_load(f)
            # Load the service account credentials from the JSON file
            self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")

            if not self.creds_path:
                logger.error("Missing GOOGLE_CREDENTIALS_PATH value")
                # exit()

            logger.info("Google Credentials found, attempting to establish connection to GDocs API server")
            self.credentials = service_account.Credentials.from_service_account_file(self.creds_path, scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly"], )

            # Build the Sheets API client
            self.service = build("sheets", "v4", credentials=self.credentials)
            self.sheets = self.service.spreadsheets()
        except Exception as e:
            logger.error(e)
            logger.error("Error during GDoc object setup")

    def set_sheet_id(self, sheet_id: str) -> None:
        self.sheet_id = sheet_id

    def get_data_from_sheet(self, sheet_name: str, cell_range: str = None) -> list:
        logger.info("Retrieving data from GDoc sheet...")
        try:
            if not cell_range:
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=sheet_name).execute()
            else:
                a1_range = self.a1notation_builder(sheet_name=sheet_name, cell_range=cell_range)
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=a1_range).execute()

            data = data.get('values', [])

            return data
        except Exception as e:
            logger.error(e)
            logger.error("Unable to get data from GDoc sheet")
            return []

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1format = f"{sheet_name}!{cell_range}"
        return a1format
