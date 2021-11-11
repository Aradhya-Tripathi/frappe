import frappe


def setup_database(force, source_sql=None, verbose=False, db_path=None):
    root_conn = get_root_connection(db_path)
    root_conn.commit()
    root_conn.sql("DROP DATABASE IF EXISTS `{0}`".format(frappe.conf.db_name))
    root_conn.sql("DROP USER IF EXISTS {0}".format(frappe.conf.db_name))
    root_conn.sql("CREATE DATABASE `{0}`".format(frappe.conf.db_name))
    root_conn.sql(
        "CREATE user {0} password '{1}'".format(
            frappe.conf.db_name, frappe.conf.db_password
        )
    )
    root_conn.sql(
        "GRANT ALL PRIVILEGES ON DATABASE `{0}` TO {0}".format(frappe.conf.db_name)
    )
    root_conn.close()

    bootstrap_database(frappe.conf.db_name, verbose, source_sql=source_sql)
    frappe.connect()


def bootstrap_database(*args, **kwargs):
    pass


def get_root_connection(db_path: str):
    if not frappe.local.flags.root_connection:
        frappe.local.flags.root_connection = frappe.database.get_db(db_path=db_path)

    return frappe.local.flags.root_connection
