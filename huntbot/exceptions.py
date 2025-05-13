"""
Centralized exceptions file for the HuntBot application.
This file contains all custom exception classes used across the application.
"""

class TableDataImportException(Exception):
    """Exception raised for errors when importing table data."""

    def __init__(self, message="Table data import error occurred", table_name=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic table name
        self.table_name = table_name

    def __str__(self):
        # Customize the string representation of the exception
        if self.table_name:
            return f'{self.args[0]} (Table: {self.table_name})'
        return self.args[0]


class ConfigurationException(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message="Configuration error occurred", config_key=None):
        # Call the base class constructor with the message
        super().__init__(message)

        # Optionally store extra information, like the problematic config key
        self.config_key = config_key

    def __str__(self):
        # Customize the string representation of the exception
        if self.config_key:
            return f'{self.args[0]} (Config key: {self.config_key})'
        return self.args[0] 