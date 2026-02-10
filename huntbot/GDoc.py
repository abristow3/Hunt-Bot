from googleapiclient.discovery import build
from google.oauth2 import service_account
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
            # Load the service account credentials from the JSON file
            # self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
            self.creds_path = "google_auth.json"

            logger.info(f"[GDoc] GOOGLE CREDS PATH: {self.creds_path}")

            if not self.creds_path:
                logger.error("[GDoc] Missing GOOGLE_CREDENTIALS_PATH value")

            logger.info("[GDoc] Google Credentials found, attempting to establish connection to GDocs API server")
            self.credentials = service_account.Credentials.from_service_account_file(self.creds_path, scopes=[
                "https://www.googleapis.com/auth/spreadsheets"], )

            # Build the Sheets API client
            self.service = build("sheets", "v4", credentials=self.credentials)
            self.sheets = self.service.spreadsheets()
        except Exception as e:
            logger.error("[GDoc] Error during GDoc object setup", exc_info=e)

    def set_sheet_id(self, sheet_id: str) -> None:
        self.sheet_id = sheet_id

    def get_data_from_sheet(self, sheet_name: str, cell_range: str = None) -> list:
        logger.info("[GDoc] Retrieving data from GDoc sheet...")
        try:
            if not cell_range:
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=sheet_name).execute()
            else:
                a1_range = self.a1notation_builder(sheet_name=sheet_name, cell_range=cell_range)
                data = self.sheets.values().get(spreadsheetId=self.sheet_id, range=a1_range).execute()

            data = data.get('values', [])

            return data
        except Exception as e:
            logger.error("[GDoc] Unable to get data from GDoc sheet", exc_info=e)
            return []

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1format = f"{sheet_name}!{cell_range}"
        return a1format

    def write_to_sheet(self, spreadsheet_id: str, sheet_name: str, cell: str, value) -> bool:
        try:
            a1_range = self.a1notation_builder(sheet_name, cell)
            body = {"values": [[value]]}

            self.sheets.values().update(spreadsheetId=spreadsheet_id, range=a1_range, valueInputOption="RAW",
                                        body=body).execute()

            return True
        except Exception as e:
            logger.error("[Gdoc] Unable to write to Flux RL Plugin Config GDoc sheet", exc_info=e)
            return False


if __name__ == "__main__":
    gdoc = GDoc()

    gdoc.set_sheet_id("1GkD8uJsI2TCgx50ZXwf7DZiB3zwOxd6MvOkJfpER2oE")
    data = gdoc.get_data_from_sheet("BotConfig")

    WRITE_SHEET_ID = "1qqkjx4YjuQ9FIBDgAGzSpmoKcDow3yEa9lYFmc-JeDA"

    gdoc.write_to_sheet(
        spreadsheet_id=WRITE_SHEET_ID,
        sheet_name="Hunt",
        cell="O3",
        value="Hi from HuntBot"
    )
