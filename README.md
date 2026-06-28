# PulseIT

PulseIT is a full-stack IT operations dashboard for managing technology assets and service-desk tickets. It provides a responsive overview of device health, support workload, ownership, and recent activity.

## Features

- Dashboard metrics for asset health and ticket workload
- Searchable asset inventory with status and device-type filters
- Device ownership, location, network, warranty, and lifecycle details
- Service-ticket creation, prioritization, assignment, and status tracking
- Relationships between tickets and affected assets
- Recent operations activity
- Responsive navigation and accessible form controls
- JSON endpoint for aggregate reporting data
- Automatic setup with realistic demonstration data

## Technology

| Layer | Technology |
| --- | --- |
| Backend | Python and Flask |
| Database | SQLite |
| Frontend | Jinja, semantic HTML, custom CSS, and vanilla JavaScript |
| Testing | Python `unittest` and the Flask test client |

SQLite foreign keys, indexed status fields, parameterized queries, server-side validation, and an application factory keep the implementation reliable and testable. No frontend build process or external database is required.

## Getting started

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### macOS and Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The local database and demonstration records are created automatically on first launch.

## Testing

```bash
python -m unittest discover -v
```

The test suite uses an isolated temporary database and covers page rendering, search filters, form validation, record creation, ticket status changes, API output, and error handling.

## Project structure

```text
ITDashboard/
|-- app/
|   |-- static/       # Styles and browser interactions
|   |-- templates/    # Dashboard, inventory, ticket, and form views
|   |-- __init__.py   # Flask application factory
|   |-- db.py         # Database lifecycle and demonstration data
|   |-- routes.py     # Application workflows and API
|   `-- schema.sql    # Relational schema and indexes
|-- tests/
|   `-- test_app.py   # Application tests
|-- run.py
`-- requirements.txt
```

## API

`GET /api/overview` returns current asset and ticket totals grouped by status:

```json
{
  "assets": {
    "Maintenance": 1,
    "Offline": 2,
    "Online": 7,
    "Warning": 2
  },
  "tickets": {
    "In Progress": 2,
    "Open": 3,
    "Resolved": 2,
    "Waiting": 1
  },
  "generated_at": "2026-06-28T10:30:00"
}
```

## License

This project is available under the [MIT License](LICENSE).
