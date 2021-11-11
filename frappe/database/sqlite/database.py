import sqlite3

import frappe
from frappe.database.database import Database


class SQLite(Database):
    def setup_type_map(self):
        self.db_type = "sqlite"
        self.type_map = {
            "Currency": ("decimal", "21,9"),
            "Int": ("bigint", None),
            "Long Int": ("bigint", None),
            "Float": ("decimal", "21,9"),
            "Percent": ("decimal", "21,9"),
            "Check": ("smallint", None),
            "Small Text": ("text", ""),
            "Long Text": ("text", ""),
            "Code": ("text", ""),
            "Text Editor": ("text", ""),
            "Markdown Editor": ("text", ""),
            "HTML Editor": ("text", ""),
            "Date": ("date", ""),
            "Datetime": ("timestamp", None),
            "Time": ("time", "6"),
            "Text": ("text", ""),
            "Data": ("varchar", self.VARCHAR_LEN),
            "Link": ("varchar", self.VARCHAR_LEN),
            "Dynamic Link": ("varchar", self.VARCHAR_LEN),
            "Password": ("text", ""),
            "Select": ("varchar", self.VARCHAR_LEN),
            "Rating": ("smallint", None),
            "Read Only": ("varchar", self.VARCHAR_LEN),
            "Attach": ("text", ""),
            "Attach Image": ("text", ""),
            "Signature": ("text", ""),
            "Color": ("varchar", self.VARCHAR_LEN),
            "Barcode": ("text", ""),
            "Geolocation": ("text", ""),
            "Duration": ("decimal", "21,9"),
            "Icon": ("varchar", self.VARCHAR_LEN),
        }

    def get_connection(self):
        if not self.db_path:
            self.db_path = frappe.conf.db_path
        conn = sqlite3.connect(self.db_path)
        return conn
