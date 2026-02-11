from googleapiclient.discovery import build
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)


class GDoc:
    def __init__(self) -> None:
        self.service = None
        self.sheets = None
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

    def get_data_from_sheet(self, spreadsheet_id: str, sheet_name: str, cell_range: str = None) -> list:
        try:
            if not cell_range:
                data = self.sheets.values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
            else:
                a1_range = self.a1notation_builder(sheet_name, cell_range)
                data = self.sheets.values().get(spreadsheetId=spreadsheet_id, range=a1_range).execute()

            return data.get('values', [])
        except Exception as e:
            logger.error("Unable to get data", exc_info=e)
            return []

    @staticmethod
    def a1notation_builder(sheet_name: str, cell_range: str) -> str:
        a1format = f"{sheet_name}!{cell_range}"
        return a1format

    def write_cell(self, spreadsheet_id: str, sheet_name: str, cell: str, value) -> bool:
        """
        Writes a single value to one specific cell.

        Example:
            cell="F1"
            value="hello"

        Will write:
            F1 = hello
        """
        try:
            a1_range = self.a1notation_builder(sheet_name, cell)

            body = {
                "values": [[value]]  # single cell must still be 2D
            }

            self.sheets.values().update(spreadsheetId=spreadsheet_id, range=a1_range, valueInputOption="RAW",
                                        body=body).execute()

            return True

        except Exception as e:
            logger.error("[GDoc] Unable to write single cell", exc_info=e)
            return False

    def write_column(self, spreadsheet_id: str, sheet_name: str, start_cell: str, values: list) -> bool:
        """
        Writes a 1D list of values vertically (as a column)
        starting from the given A1 cell.
        Example:
            start_cell="F1"
            values=["a", "b", "c"]
        Will write:
            F1 = a
            F2 = b
            F3 = c
        """
        try:
            if not isinstance(values, list):
                raise ValueError("values must be a list")

            a1_range = self.a1notation_builder(sheet_name, start_cell)

            # Convert 1D list to column format required by Google Sheets API
            body = {
                "values": [[value] for value in values]
            }

            self.sheets.values().update(spreadsheetId=spreadsheet_id, range=a1_range, valueInputOption="RAW",
                                        body=body).execute()

            return True

        except Exception as e:
            logger.error("[GDoc] Unable to write column to sheet", exc_info=e)
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    SPREADSHEET_ID = "1qqkjx4YjuQ9FIBDgAGzSpmoKcDow3yEa9lYFmc-JeDA"
    SHEET_NAME = "Hunt"

    gdoc = GDoc()

    # ------------------------
    # Test 1: Write list to column F starting at F1
    # ------------------------
    test_list = ["apple", "banana", "cherry"]
    success_list = gdoc.write_column(
        spreadsheet_id=SPREADSHEET_ID,
        sheet_name=SHEET_NAME,
        start_cell="F1",
        values=test_list,
    )

    print(f"Column F write success: {success_list}")


    # ------------------------
    # Test 3: Write single cell
    # ------------------------
    success_cell = gdoc.write_cell(
        spreadsheet_id=SPREADSHEET_ID,
        sheet_name=SHEET_NAME,
        cell="H1",
        value="Single Cell Test"
    )

    print(f"Single cell write success (J1): {success_cell}")


