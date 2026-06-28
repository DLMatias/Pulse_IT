import sqlite3
from datetime import date, datetime, timedelta

import click
from flask import current_app, g


sqlite3.register_adapter(date, lambda value: value.isoformat())
sqlite3.register_adapter(datetime, lambda value: value.isoformat(sep=" "))
sqlite3.register_converter("date", lambda value: date.fromisoformat(value.decode()))
sqlite3.register_converter(
    "timestamp", lambda value: datetime.fromisoformat(value.decode())
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exception=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_database():
    database = get_db()
    with current_app.open_resource("schema.sql") as schema:
        database.executescript(schema.read().decode("utf8"))
    database.commit()


def seed_database():
    database = get_db()
    existing = database.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
    if existing:
        return

    now = datetime.now().replace(microsecond=0)
    today = date.today()
    assets = [
        ("LAP-1042", "MacBook Pro - Design", "Laptop", "Apple", "MacBook Pro 14", "macOS 15.5", "10.20.1.42", "Maya Chen", "Design", "New York", "Online", now - timedelta(minutes=3), today - timedelta(days=420), today + timedelta(days=675)),
        ("LAP-1038", "ThinkPad T14 - Finance", "Laptop", "Lenovo", "ThinkPad T14 Gen 4", "Windows 11 Pro", "10.20.1.38", "Daniel Ortiz", "Finance", "New York", "Warning", now - timedelta(minutes=18), today - timedelta(days=610), today + timedelta(days=485)),
        ("WS-2081", "Engineering Workstation 01", "Workstation", "Dell", "Precision 5860", "Windows 11 Pro", "10.20.2.81", "Priya Shah", "Engineering", "Boston", "Online", now - timedelta(minutes=1), today - timedelta(days=280), today + timedelta(days=815)),
        ("SRV-0012", "Identity Services", "Server", "HPE", "ProLiant DL360", "Ubuntu Server 24.04", "10.20.10.12", "Infrastructure Team", "IT", "New York DC", "Online", now - timedelta(seconds=40), today - timedelta(days=760), today + timedelta(days=335)),
        ("SRV-0018", "File Services", "Server", "Dell", "PowerEdge R650", "Windows Server 2022", "10.20.10.18", "Infrastructure Team", "IT", "New York DC", "Warning", now - timedelta(minutes=7), today - timedelta(days=820), today + timedelta(days=275)),
        ("NET-0044", "Boston Core Switch", "Network", "Cisco", "Catalyst 9300", "IOS XE 17.12", "10.21.0.44", "Network Team", "IT", "Boston", "Online", now - timedelta(seconds=20), today - timedelta(days=540), today + timedelta(days=555)),
        ("LAP-1049", "Latitude 7440 - Sales", "Laptop", "Dell", "Latitude 7440", "Windows 11 Pro", "10.20.1.49", "Jordan Kim", "Sales", "Remote", "Offline", now - timedelta(hours=3, minutes=22), today - timedelta(days=510), today + timedelta(days=585)),
        ("PRN-0021", "Marketing Color Printer", "Printer", "HP", "Color LaserJet MFP", "FutureSmart 5.8", "10.20.3.21", "Marketing Team", "Marketing", "New York", "Maintenance", now - timedelta(days=1, hours=2), today - timedelta(days=980), today + timedelta(days=115)),
        ("LAP-1053", "MacBook Air - Marketing", "Laptop", "Apple", "MacBook Air 15", "macOS 15.5", "10.20.1.53", "Sofia Williams", "Marketing", "New York", "Online", now - timedelta(minutes=6), today - timedelta(days=190), today + timedelta(days=905)),
        ("TAB-0016", "iPad - Field Operations", "Tablet", "Apple", "iPad Air", "iPadOS 18.5", "10.22.1.16", "Field Operations", "Operations", "Remote", "Online", now - timedelta(minutes=13), today - timedelta(days=340), today + timedelta(days=755)),
        ("WS-2088", "QA Test Workstation", "Workstation", "HP", "Z2 G9 Tower", "Windows 11 Pro", "10.20.2.88", "Alex Morgan", "Engineering", "Boston", "Online", now - timedelta(minutes=2), today - timedelta(days=330), today + timedelta(days=765)),
        ("NET-0051", "New York Guest AP", "Network", "Ubiquiti", "U6 Enterprise", "UniFi 8.1", "10.20.0.51", "Network Team", "IT", "New York", "Offline", now - timedelta(hours=1, minutes=8), today - timedelta(days=450), today + timedelta(days=645)),
    ]

    database.executemany(
        """
        INSERT INTO assets (
            asset_tag, name, type, manufacturer, model, operating_system,
            ip_address, assigned_to, department, location, status, last_seen,
            purchase_date, warranty_end
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        assets,
    )

    asset_ids = {
        row["asset_tag"]: row["id"]
        for row in database.execute("SELECT id, asset_tag FROM assets")
    }
    tickets = [
        ("INC-1048", "VPN access failing after password reset", "User receives an authentication loop when connecting from home.", "Daniel Ortiz", "daniel.ortiz@example.com", "Finance", "Access", "High", "In Progress", "Sam Rivera", asset_ids["LAP-1038"], now - timedelta(hours=2, minutes=14), now - timedelta(minutes=35), None),
        ("INC-1047", "Shared drive approaching storage limit", "Finance shared drive has exceeded 90% capacity.", "System Monitor", "monitoring@example.com", "IT", "Infrastructure", "Critical", "Open", "Morgan Lee", asset_ids["SRV-0018"], now - timedelta(hours=3, minutes=8), now - timedelta(hours=3, minutes=8), None),
        ("REQ-1046", "Adobe Creative Cloud license request", "New team member needs access to the design software suite.", "Sofia Williams", "sofia.williams@example.com", "Marketing", "Software", "Medium", "Waiting", "Taylor Brooks", asset_ids["LAP-1053"], now - timedelta(hours=5, minutes=42), now - timedelta(hours=1, minutes=5), None),
        ("INC-1045", "Intermittent Wi-Fi in conference room", "Guest network drops during video calls in Hudson conference room.", "Casey Johnson", "casey.johnson@example.com", "Operations", "Network", "High", "Open", "Morgan Lee", asset_ids["NET-0051"], now - timedelta(hours=7, minutes=19), now - timedelta(hours=7, minutes=19), None),
        ("INC-1044", "Color printer leaving streaks", "Print quality declined after the latest toner replacement.", "Avery Thompson", "avery.thompson@example.com", "Marketing", "Hardware", "Medium", "In Progress", "Taylor Brooks", asset_ids["PRN-0021"], now - timedelta(days=1, hours=1), now - timedelta(hours=4), None),
        ("REQ-1043", "New employee equipment setup", "Prepare laptop, monitor, and account access for Monday start.", "HR Service Desk", "hr@example.com", "People", "Onboarding", "Low", "Open", "Sam Rivera", None, now - timedelta(days=1, hours=5), now - timedelta(days=1, hours=5), None),
        ("INC-1042", "Laptop battery draining quickly", "Battery drops from full to 20% in under two hours.", "Jordan Kim", "jordan.kim@example.com", "Sales", "Hardware", "Medium", "Resolved", "Taylor Brooks", asset_ids["LAP-1049"], now - timedelta(days=2, hours=3), now - timedelta(days=1, hours=6), now - timedelta(days=1, hours=6)),
        ("REQ-1041", "GitHub repository access", "Add new QA engineer to the application engineering organization.", "Alex Morgan", "alex.morgan@example.com", "Engineering", "Access", "Low", "Resolved", "Sam Rivera", asset_ids["WS-2088"], now - timedelta(days=3), now - timedelta(days=2, hours=18), now - timedelta(days=2, hours=18)),
    ]
    database.executemany(
        """
        INSERT INTO tickets (
            ticket_number, title, description, requester, requester_email,
            department, category, priority, status, assigned_to, asset_id,
            created_at, updated_at, resolved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tickets,
    )

    activities = [
        ("updated", "ticket", None, "Sam moved INC-1048 to In Progress", now - timedelta(minutes=35)),
        ("detected", "asset", asset_ids["NET-0051"], "New York Guest AP went offline", now - timedelta(hours=1, minutes=8)),
        ("commented", "ticket", None, "Sofia added a note to REQ-1046", now - timedelta(hours=1, minutes=5)),
        ("created", "ticket", None, "System Monitor opened critical ticket INC-1047", now - timedelta(hours=3, minutes=8)),
        ("maintenance", "asset", asset_ids["PRN-0021"], "Marketing Color Printer entered maintenance", now - timedelta(hours=4)),
        ("resolved", "ticket", None, "Taylor resolved INC-1042", now - timedelta(days=1, hours=6)),
    ]
    database.executemany(
        """
        INSERT INTO activities (action, entity_type, entity_id, description, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        activities,
    )
    database.commit()


@click.command("init-db")
def init_db_command():
    init_database()
    click.echo("Database initialized.")


@click.command("seed-db")
def seed_db_command():
    seed_database()
    click.echo("Sample data added.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_db_command)
