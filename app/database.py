import json
import sqlite3
import uuid
from datetime import UTC, datetime

from flask import current_app, g


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE_PATH"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL,
            image_path TEXT NOT NULL,
            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    db.commit()


def insert_report(*, payload, image_path, report):
    report_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    db = get_db()
    db.execute(
        """
        INSERT INTO reports (
            id, description, location, phone, image_path, report_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            payload.description,
            payload.location,
            payload.phone,
            str(image_path),
            json.dumps(report, sort_keys=True),
            created_at,
        ),
    )
    db.commit()
    return {
        "id": report_id,
        "description": payload.description,
        "location": payload.location,
        "phone": payload.phone,
        "image_path": str(image_path),
        "created_at": created_at,
    }


def get_report(report_id):
    row = get_db().execute(
        """
        SELECT id, description, location, phone, image_path, report_json, created_at
        FROM reports
        WHERE id = ?
        """,
        (report_id,),
    ).fetchone()
    if row is None:
        return None

    return {
        "submission": {
            "id": row["id"],
            "description": row["description"],
            "location": row["location"],
            "phone": row["phone"],
            "image_path": row["image_path"],
            "created_at": row["created_at"],
        },
        "report": json.loads(row["report_json"]),
    }
