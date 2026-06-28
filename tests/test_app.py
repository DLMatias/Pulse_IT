import os
import tempfile
import unittest

from app import create_app
from app.db import get_db


class PulseITTestCase(unittest.TestCase):
    def setUp(self):
        self.database_fd, self.database_path = tempfile.mkstemp()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.database_path,
                "SEED_DATABASE": True,
                "SECRET_KEY": "test-key",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.database_fd)
        os.unlink(self.database_path)

    def test_primary_pages_render(self):
        for path in ("/", "/assets", "/assets/1", "/tickets", "/tickets/1"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_dashboard_contains_seed_metrics(self):
        response = self.client.get("/")
        self.assertIn(b"Total managed assets", response.data)
        self.assertIn(b"12", response.data)
        self.assertIn(b"Critical incidents", response.data)

    def test_asset_filters(self):
        response = self.client.get("/assets?status=Offline&type=Laptop")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Latitude 7440", response.data)
        self.assertNotIn(b"Boston Core Switch", response.data)

    def test_create_asset(self):
        response = self.client.post(
            "/assets/new",
            data={
                "asset_tag": "LAP-2001",
                "name": "Test Laptop",
                "type": "Laptop",
                "manufacturer": "Framework",
                "model": "Laptop 13",
                "operating_system": "Ubuntu 24.04",
                "ip_address": "10.20.1.99",
                "assigned_to": "Jamie Test",
                "department": "IT",
                "location": "Boston",
                "status": "Online",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Asset added to inventory", response.data)
        self.assertIn(b"Test Laptop", response.data)

        with self.app.app_context():
            created = get_db().execute(
                "SELECT * FROM assets WHERE asset_tag = 'LAP-2001'"
            ).fetchone()
            self.assertIsNotNone(created)
            self.assertEqual(created["assigned_to"], "Jamie Test")

    def test_asset_validation_rejects_incomplete_form(self):
        response = self.client.post("/assets/new", data={"name": "Incomplete"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"This field is required", response.data)

    def test_create_and_resolve_ticket(self):
        response = self.client.post(
            "/tickets/new",
            data={
                "title": "Cannot connect to office Wi-Fi",
                "description": "Connection fails after entering credentials.",
                "requester": "Jamie Test",
                "requester_email": "jamie@example.com",
                "department": "Sales",
                "category": "Network",
                "priority": "High",
                "assigned_to": "Sam Rivera",
                "asset_id": "1",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"created successfully", response.data)
        self.assertIn(b"Cannot connect to office Wi-Fi", response.data)

        with self.app.app_context():
            ticket = get_db().execute(
                "SELECT * FROM tickets WHERE title = ?",
                ("Cannot connect to office Wi-Fi",),
            ).fetchone()
            ticket_id = ticket["id"]

        response = self.client.post(
            f"/tickets/{ticket_id}",
            data={"status": "Resolved"},
            follow_redirects=True,
        )
        self.assertIn(b"Ticket status updated", response.data)
        self.assertIn(b"Resolved", response.data)

    def test_api_overview_returns_json(self):
        response = self.client.get("/api/overview")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(sum(payload["assets"].values()), 12)
        self.assertIn("Open", payload["tickets"])

    def test_unknown_route_uses_custom_404(self):
        response = self.client.get("/not-a-page")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"stepped away from its desk", response.data)


if __name__ == "__main__":
    unittest.main()

