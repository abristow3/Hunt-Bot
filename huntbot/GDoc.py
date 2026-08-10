from googleapiclient.discovery import build
from google.oauth2 import service_account
import logging
import pandas as pd
import os

logger = logging.getLogger(__name__)


class GDoc:
    def __init__(self) -> None:
        self.service = None
        self.sheets = None
        self.creds_path = ""
        self.credentials = ""
        self.command_channel_id = 0

        self.on_startup()

    def on_startup(self) -> None:
        try:
            # Load the service account credentials from the JSON file
            self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
            # self.creds_path = "huntbot/google_auth.json"

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

    def get_data_from_sheet(self, spreadsheet_id: str, sheet_name: str, cell_range: str = None) -> pd.DataFrame:
        try:
            if not cell_range:
                data = self.sheets.values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
            else:
                a1_range = self.a1notation_builder(sheet_name, cell_range)
                data = self.sheets.values().get(spreadsheetId=spreadsheet_id, range=a1_range).execute()

            values = data.get("values", [])
            return self.build_dataframe(values)
        except Exception as e:
            logger.error("Unable to get data", exc_info=e)
            return pd.DataFrame()

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

    @staticmethod
    def build_dataframe(data: list[list]) -> pd.DataFrame:
        try:
            df = pd.DataFrame(data)
            df.iloc[0] = df.iloc[0].replace({"": None})
            return df
        except Exception as e:
            logger.error(e)
            logger.error("Error creating DataFrame")
            return pd.DataFrame()

    @staticmethod
    def build_table_map(df: pd.DataFrame) -> dict:
        logger.info("Building table map...")

        table_map = {}
        start_col = None
        name = ""

        try:
            for col in range(len(df.columns)):
                header_value = df.iloc[0, col]

                if header_value is not None:
                    name = header_value
                    start_col = col
                    table_map[name] = {"start_col": start_col}

                else:
                    if name:
                        table_map.setdefault(name, {})["end_col"] = col

            return table_map

        except Exception as e:
            logger.error(e)
            logger.error("Error building table map")
            return {}

    @staticmethod
    def extract_table(df: pd.DataFrame, table_map: dict, table_name: str) -> pd.DataFrame:

        logger.info("Pulling Table Data...")

        table_metadata = table_map.get(table_name)
        if not table_metadata:
            return pd.DataFrame()

        start_col = table_metadata["start_col"]
        end_col = table_metadata.get("end_col", start_col)

        logger.info(f"Data located between columns {start_col} and {end_col}")

        table_df = df.iloc[:, start_col:end_col + 1].copy()

        # Drop merged label row
        table_df = table_df.drop(index=0).reset_index(drop=True)

        # Clean data
        table_df = table_df.replace("", pd.NA)
        table_df = table_df.dropna(axis=1, how="all")
        table_df = table_df.dropna(how="all")

        # Promote header row
        table_df.columns = table_df.iloc[0]
        table_df = table_df.drop(index=0).reset_index(drop=True)

        return table_df

    @staticmethod
    def clean_to_oneliner(text: str, sep: str = " | ") -> str:
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]  # drop empty lines
        return sep.join(lines)

    def read_column(self, spreadsheet_id: str, sheet_name: str, column: str = "A") -> list:
        """
        Reads all values from a single column (e.g. "A") and returns them as a flat list of strings.
        """
        try:
            a1_range = self.a1notation_builder(sheet_name, f"{column}:{column}")
            data = self.sheets.values().get(spreadsheetId=spreadsheet_id, range=a1_range).execute()
            values = data.get("values", [])
            return [row[0] if row else "" for row in values]
        except Exception as e:
            logger.error("[GDoc] Unable to read column", exc_info=e)
            return []

    def write_cell_by_key(self, spreadsheet_id: str, sheet_name: str, key: str, value, key_column: str = "A",
                          value_column: str = "B") -> bool:
        """
        Finds `key` in `key_column` and writes `value` into the same row in `value_column`.

        Example:
            key_column="A" contains "Bounty Description" in row 18
            value_column="B"
        Will write:
            B18 = value
        """
        column_values = self.read_column(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name, column=key_column)

        row_number = None
        for i, cell_value in enumerate(column_values, start=1):
            if cell_value.strip() == key:
                row_number = i
                break

        if row_number is None:
            logger.error(f"[GDoc] Key '{key}' not found in column {key_column} of sheet '{sheet_name}'")
            return False

        target_cell = f"{value_column}{row_number}"
        return self.write_cell(spreadsheet_id=spreadsheet_id, sheet_name=sheet_name, cell=target_cell, value=value)
