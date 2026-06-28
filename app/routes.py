from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .db import get_db


bp = Blueprint("main", __name__)

ASSET_STATUSES = ("Online", "Warning", "Offline", "Maintenance")
ASSET_TYPES = ("Laptop", "Workstation", "Server", "Network", "Printer", "Tablet", "Other")
TICKET_STATUSES = ("Open", "In Progress", "Waiting", "Resolved")
TICKET_PRIORITIES = ("Low", "Medium", "High", "Critical")
TICKET_CATEGORIES = ("Access", "Hardware", "Infrastructure", "Network", "Onboarding", "Software", "Other")


def record_activity(action, entity_type, entity_id, description):
    database = get_db()
    database.execute(
        """
        INSERT INTO activities (action, entity_type, entity_id, description)
        VALUES (?, ?, ?, ?)
        """,
        (action, entity_type, entity_id, description),
    )


def validate_required(form, fields):
    return {
        field: "This field is required."
        for field in fields
        if not form.get(field, "").strip()
    }


@bp.app_template_filter("relative_time")
def relative_time(value):
    if not value:
        return "Never"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    seconds = max(0, int((datetime.now() - value).total_seconds()))
    if seconds < 60:
        return "Just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} min ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr ago"
    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


@bp.app_template_filter("date_display")
def date_display(value):
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%b %d, %Y")


@bp.app_template_filter("datetime_display")
def datetime_display(value):
    if not value:
        return "—"
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%b %d, %Y · %I:%M %p")


@bp.context_processor
def template_globals():
    now = datetime.now()
    return {
        "current_year": now.year,
        "today_label": now.strftime("%A, %B %d").replace(" 0", " "),
    }


@bp.route("/")
def dashboard():
    database = get_db()
    asset_summary = database.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(status = 'Online') AS online,
            SUM(status = 'Warning') AS warning,
            SUM(status = 'Offline') AS offline,
            SUM(status = 'Maintenance') AS maintenance
        FROM assets
        """
    ).fetchone()
    ticket_summary = database.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(status != 'Resolved') AS active,
            SUM(priority = 'Critical' AND status != 'Resolved') AS critical,
            SUM(status = 'Resolved') AS resolved
        FROM tickets
        """
    ).fetchone()
    status_counts = database.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM tickets
        GROUP BY status
        ORDER BY CASE status
            WHEN 'Open' THEN 1 WHEN 'In Progress' THEN 2
            WHEN 'Waiting' THEN 3 ELSE 4 END
        """
    ).fetchall()
    asset_types = database.execute(
        """
        SELECT type, COUNT(*) AS count
        FROM assets
        GROUP BY type
        ORDER BY count DESC, type
        """
    ).fetchall()
    priority_tickets = database.execute(
        """
        SELECT tickets.*, assets.asset_tag
        FROM tickets
        LEFT JOIN assets ON tickets.asset_id = assets.id
        WHERE tickets.status != 'Resolved'
        ORDER BY CASE tickets.priority
            WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
            WHEN 'Medium' THEN 3 ELSE 4 END,
            tickets.created_at ASC
        LIMIT 5
        """
    ).fetchall()
    recent_activity = database.execute(
        "SELECT * FROM activities ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    online_percent = round(
        (asset_summary["online"] or 0) / asset_summary["total"] * 100
    ) if asset_summary["total"] else 0
    resolution_percent = round(
        (ticket_summary["resolved"] or 0) / ticket_summary["total"] * 100
    ) if ticket_summary["total"] else 0

    return render_template(
        "dashboard.html",
        asset_summary=asset_summary,
        ticket_summary=ticket_summary,
        status_counts=status_counts,
        asset_types=asset_types,
        priority_tickets=priority_tickets,
        recent_activity=recent_activity,
        online_percent=online_percent,
        resolution_percent=resolution_percent,
    )


@bp.route("/assets")
def assets():
    database = get_db()
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    asset_type = request.args.get("type", "").strip()
    conditions = []
    parameters = []

    if query:
        conditions.append(
            "(name LIKE ? OR asset_tag LIKE ? OR assigned_to LIKE ? OR model LIKE ?)"
        )
        wildcard = f"%{query}%"
        parameters.extend([wildcard] * 4)
    if status in ASSET_STATUSES:
        conditions.append("status = ?")
        parameters.append(status)
    if asset_type in ASSET_TYPES:
        conditions.append("type = ?")
        parameters.append(asset_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    asset_rows = database.execute(
        f"""
        SELECT * FROM assets
        {where_clause}
        ORDER BY CASE status
            WHEN 'Offline' THEN 1 WHEN 'Warning' THEN 2
            WHEN 'Maintenance' THEN 3 ELSE 4 END,
            name
        """,
        parameters,
    ).fetchall()
    return render_template(
        "assets.html",
        assets=asset_rows,
        statuses=ASSET_STATUSES,
        asset_types=ASSET_TYPES,
        filters={"q": query, "status": status, "type": asset_type},
    )


@bp.route("/assets/new", methods=("GET", "POST"))
def asset_create():
    errors = {}
    if request.method == "POST":
        errors = validate_required(
            request.form,
            ("asset_tag", "name", "type", "manufacturer", "model", "location", "status"),
        )
        if request.form.get("status") not in ASSET_STATUSES:
            errors["status"] = "Select a valid status."
        if request.form.get("type") not in ASSET_TYPES:
            errors["type"] = "Select a valid asset type."

        database = get_db()
        duplicate = database.execute(
            "SELECT id FROM assets WHERE asset_tag = ?",
            (request.form.get("asset_tag", "").strip().upper(),),
        ).fetchone()
        if duplicate:
            errors["asset_tag"] = "That asset tag is already in use."

        if not errors:
            cursor = database.execute(
                """
                INSERT INTO assets (
                    asset_tag, name, type, manufacturer, model, operating_system,
                    ip_address, assigned_to, department, location, status,
                    last_seen, purchase_date, warranty_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                asset_form_values(request.form, include_tag=True),
            )
            record_activity(
                "created",
                "asset",
                cursor.lastrowid,
                f"{request.form['asset_tag'].strip().upper()} was added to inventory",
            )
            database.commit()
            flash("Asset added to inventory.", "success")
            return redirect(url_for("main.assets"))

    return render_template(
        "asset_form.html",
        asset=None,
        errors=errors,
        statuses=ASSET_STATUSES,
        asset_types=ASSET_TYPES,
    )


def asset_form_values(form, include_tag=False):
    values = []
    if include_tag:
        values.append(form.get("asset_tag", "").strip().upper())
    values.extend(
        [
            form.get("name", "").strip(),
            form.get("type", "").strip(),
            form.get("manufacturer", "").strip(),
            form.get("model", "").strip(),
            form.get("operating_system", "").strip() or None,
            form.get("ip_address", "").strip() or None,
            form.get("assigned_to", "").strip() or None,
            form.get("department", "").strip() or None,
            form.get("location", "").strip(),
            form.get("status", "").strip(),
            datetime.now().replace(microsecond=0),
            form.get("purchase_date", "") or None,
            form.get("warranty_end", "") or None,
        ]
    )
    return values


def get_asset_or_404(asset_id):
    asset = get_db().execute(
        "SELECT * FROM assets WHERE id = ?", (asset_id,)
    ).fetchone()
    if asset is None:
        abort(404)
    return asset


@bp.route("/assets/<int:asset_id>")
def asset_detail(asset_id):
    asset = get_asset_or_404(asset_id)
    linked_tickets = get_db().execute(
        """
        SELECT * FROM tickets
        WHERE asset_id = ?
        ORDER BY created_at DESC
        """,
        (asset_id,),
    ).fetchall()
    return render_template(
        "asset_detail.html", asset=asset, linked_tickets=linked_tickets
    )


@bp.route("/assets/<int:asset_id>/edit", methods=("GET", "POST"))
def asset_edit(asset_id):
    asset = get_asset_or_404(asset_id)
    errors = {}
    if request.method == "POST":
        errors = validate_required(
            request.form, ("name", "type", "manufacturer", "model", "location", "status")
        )
        if request.form.get("status") not in ASSET_STATUSES:
            errors["status"] = "Select a valid status."
        if request.form.get("type") not in ASSET_TYPES:
            errors["type"] = "Select a valid asset type."

        if not errors:
            database = get_db()
            database.execute(
                """
                UPDATE assets SET
                    name = ?, type = ?, manufacturer = ?, model = ?,
                    operating_system = ?, ip_address = ?, assigned_to = ?,
                    department = ?, location = ?, status = ?, last_seen = ?,
                    purchase_date = ?, warranty_end = ?
                WHERE id = ?
                """,
                (*asset_form_values(request.form), asset_id),
            )
            record_activity(
                "updated", "asset", asset_id, f"{asset['asset_tag']} inventory details updated"
            )
            database.commit()
            flash("Asset details updated.", "success")
            return redirect(url_for("main.asset_detail", asset_id=asset_id))

    return render_template(
        "asset_form.html",
        asset=asset,
        errors=errors,
        statuses=ASSET_STATUSES,
        asset_types=ASSET_TYPES,
    )


@bp.route("/tickets")
def tickets():
    database = get_db()
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    conditions = []
    parameters = []

    if query:
        conditions.append(
            "(ticket_number LIKE ? OR title LIKE ? OR requester LIKE ? OR assigned_to LIKE ?)"
        )
        wildcard = f"%{query}%"
        parameters.extend([wildcard] * 4)
    if status in TICKET_STATUSES:
        conditions.append("tickets.status = ?")
        parameters.append(status)
    if priority in TICKET_PRIORITIES:
        conditions.append("tickets.priority = ?")
        parameters.append(priority)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    ticket_rows = database.execute(
        f"""
        SELECT tickets.*, assets.asset_tag
        FROM tickets
        LEFT JOIN assets ON tickets.asset_id = assets.id
        {where_clause}
        ORDER BY CASE tickets.status WHEN 'Resolved' THEN 2 ELSE 1 END,
            CASE tickets.priority
                WHEN 'Critical' THEN 1 WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3 ELSE 4 END,
            tickets.created_at DESC
        """,
        parameters,
    ).fetchall()
    return render_template(
        "tickets.html",
        tickets=ticket_rows,
        statuses=TICKET_STATUSES,
        priorities=TICKET_PRIORITIES,
        filters={"q": query, "status": status, "priority": priority},
    )


def get_ticket_or_404(ticket_id):
    ticket = get_db().execute(
        """
        SELECT tickets.*, assets.asset_tag, assets.name AS asset_name
        FROM tickets
        LEFT JOIN assets ON tickets.asset_id = assets.id
        WHERE tickets.id = ?
        """,
        (ticket_id,),
    ).fetchone()
    if ticket is None:
        abort(404)
    return ticket


@bp.route("/tickets/new", methods=("GET", "POST"))
def ticket_create():
    database = get_db()
    assets_list = database.execute(
        "SELECT id, asset_tag, name FROM assets ORDER BY asset_tag"
    ).fetchall()
    errors = {}

    if request.method == "POST":
        errors = validate_required(
            request.form, ("title", "requester", "category", "priority")
        )
        if request.form.get("priority") not in TICKET_PRIORITIES:
            errors["priority"] = "Select a valid priority."
        if request.form.get("category") not in TICKET_CATEGORIES:
            errors["category"] = "Select a valid category."

        if not errors:
            next_id = database.execute(
                "SELECT COALESCE(MAX(id), 0) + 1041 FROM tickets"
            ).fetchone()[0]
            prefix = "REQ" if request.form["category"] in ("Onboarding", "Software") else "INC"
            ticket_number = f"{prefix}-{next_id}"
            cursor = database.execute(
                """
                INSERT INTO tickets (
                    ticket_number, title, description, requester, requester_email,
                    department, category, priority, status, assigned_to, asset_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?)
                """,
                (
                    ticket_number,
                    request.form["title"].strip(),
                    request.form.get("description", "").strip() or None,
                    request.form["requester"].strip(),
                    request.form.get("requester_email", "").strip() or None,
                    request.form.get("department", "").strip() or None,
                    request.form["category"],
                    request.form["priority"],
                    request.form.get("assigned_to", "").strip() or "Unassigned",
                    request.form.get("asset_id") or None,
                ),
            )
            record_activity(
                "created",
                "ticket",
                cursor.lastrowid,
                f"{ticket_number} was opened by {request.form['requester'].strip()}",
            )
            database.commit()
            flash(f"{ticket_number} created successfully.", "success")
            return redirect(url_for("main.ticket_detail", ticket_id=cursor.lastrowid))

    return render_template(
        "ticket_form.html",
        errors=errors,
        priorities=TICKET_PRIORITIES,
        categories=TICKET_CATEGORIES,
        assets=assets_list,
    )


@bp.route("/tickets/<int:ticket_id>", methods=("GET", "POST"))
def ticket_detail(ticket_id):
    ticket = get_ticket_or_404(ticket_id)
    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status not in TICKET_STATUSES:
            flash("Select a valid ticket status.", "error")
        else:
            database = get_db()
            resolved_at = (
                datetime.now().replace(microsecond=0)
                if new_status == "Resolved"
                else None
            )
            database.execute(
                """
                UPDATE tickets
                SET status = ?, updated_at = CURRENT_TIMESTAMP, resolved_at = ?
                WHERE id = ?
                """,
                (new_status, resolved_at, ticket_id),
            )
            record_activity(
                "resolved" if new_status == "Resolved" else "updated",
                "ticket",
                ticket_id,
                f"{ticket['ticket_number']} moved to {new_status}",
            )
            database.commit()
            flash("Ticket status updated.", "success")
            return redirect(url_for("main.ticket_detail", ticket_id=ticket_id))

    return render_template(
        "ticket_detail.html", ticket=ticket, statuses=TICKET_STATUSES
    )


@bp.route("/api/overview")
def api_overview():
    database = get_db()
    asset_status = {
        row["status"]: row["count"]
        for row in database.execute(
            "SELECT status, COUNT(*) AS count FROM assets GROUP BY status"
        )
    }
    ticket_status = {
        row["status"]: row["count"]
        for row in database.execute(
            "SELECT status, COUNT(*) AS count FROM tickets GROUP BY status"
        )
    }
    return jsonify(
        {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "assets": asset_status,
            "tickets": ticket_status,
        }
    )


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404
