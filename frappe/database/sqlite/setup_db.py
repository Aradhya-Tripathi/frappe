import subprocess
import frappe
import os


def setup_database(force, source_sql=None, verbose=False, db_path=None):
    root_conn = get_root_connection(db_path)
    if frappe.conf.db_type == "sqlite":
        root_conn.sql("begin")

    root_conn.commit()
    root_conn.close()

    bootstrap_database(frappe.conf.db_name, verbose, source_sql=source_sql)
    frappe.connect()


def bootstrap_database(db_name, verbose, source_sql=None):
    frappe.connect(db_name=db_name)
    if verbose:
        print("Loading in SQL from source")

    import_db_from_sql(source_sql, verbose)


def import_db_from_sql(source_sql: str = None, verbose: bool = False):
    if not source_sql:
        source_sql = os.path.join(os.path.dirname(__file__), "framework_sqlite.sql")

    print("Restoring Database file...")


def get_root_connection(db_path: str):
    if not frappe.local.flags.root_connection:
        if not db_path:
            db_path = frappe.conf.db_path
        frappe.local.flags.root_connection = frappe.database.get_db(db_path=db_path)

    return frappe.local.flags.root_connection
