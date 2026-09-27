"""
Waypoint — Project & Task Manager
Backend API built with Flask + SQLite.

Run with:  python app.py
Serves on: http://127.0.0.1:5000
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, g, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "waypoint.db"

app = Flask(__name__)
CORS(app)  # allow the frontend (any local origin) to call this API

VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Open (or reuse) a SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they do not exist yet."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT NOT NULL DEFAULT 'todo',
            priority    TEXT NOT NULL DEFAULT 'medium',
            due_date    TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def project_to_dict(row, task_counts=None):
    data = dict(row)
    if task_counts is not None:
        data["task_counts"] = task_counts
    return data


def task_to_dict(row):
    return dict(row)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": now_iso()})


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

@app.route("/api/projects", methods=["GET"])
def list_projects():
    db = get_db()
    projects = db.execute(
        "SELECT * FROM projects ORDER BY created_at DESC"
    ).fetchall()

    result = []
    for p in projects:
        counts_row = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'todo' THEN 1 ELSE 0 END) AS todo,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) AS done
            FROM tasks WHERE project_id = ?
            """,
            (p["id"],),
        ).fetchone()
        counts = {
            "total": counts_row["total"] or 0,
            "todo": counts_row["todo"] or 0,
            "in_progress": counts_row["in_progress"] or 0,
            "done": counts_row["done"] or 0,
        }
        result.append(project_to_dict(p, counts))

    return jsonify(result)


@app.route("/api/projects", methods=["POST"])
def create_project():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name:
        return jsonify({"error": "Project name is required."}), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?)",
        (name, description, now_iso()),
    )
    db.commit()
    new_row = db.execute(
        "SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(project_to_dict(new_row, {"total": 0, "todo": 0, "in_progress": 0, "done": 0})), 201


@app.route("/api/projects/<int:project_id>", methods=["PUT"])
def update_project(project_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    existing = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Project not found."}), 404

    name = (payload.get("name") or existing["name"]).strip()
    description = payload.get("description", existing["description"])

    if not name:
        return jsonify({"error": "Project name is required."}), 400

    db.execute(
        "UPDATE projects SET name = ?, description = ? WHERE id = ?",
        (name, description, project_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return jsonify(project_to_dict(updated))


@app.route("/api/projects/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    db = get_db()
    existing = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Project not found."}), 404

    db.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    return jsonify({"deleted": project_id})


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.route("/api/projects/<int:project_id>/tasks", methods=["GET"])
def list_tasks(project_id):
    db = get_db()
    project = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    tasks = db.execute(
        "SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,),
    ).fetchall()
    return jsonify([task_to_dict(t) for t in tasks])


@app.route("/api/tasks", methods=["POST"])
def create_task():
    payload = request.get_json(silent=True) or {}
    project_id = payload.get("project_id")
    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    status = payload.get("status", "todo")
    priority = payload.get("priority", "medium")
    due_date = payload.get("due_date", "")

    if not project_id:
        return jsonify({"error": "project_id is required."}), 400
    if not title:
        return jsonify({"error": "Task title is required."}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400

    db = get_db()
    project = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if project is None:
        return jsonify({"error": "Project not found."}), 404

    cur = db.execute(
        """
        INSERT INTO tasks (project_id, title, description, status, priority, due_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, title, description, status, priority, due_date, now_iso()),
    )
    db.commit()
    new_row = db.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(task_to_dict(new_row)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    existing = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Task not found."}), 404

    title = (payload.get("title") or existing["title"]).strip()
    description = payload.get("description", existing["description"])
    status = payload.get("status", existing["status"])
    priority = payload.get("priority", existing["priority"])
    due_date = payload.get("due_date", existing["due_date"])

    if not title:
        return jsonify({"error": "Task title is required."}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400

    db.execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, status = ?, priority = ?, due_date = ?
        WHERE id = ?
        """,
        (title, description, status, priority, due_date, task_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return jsonify(task_to_dict(updated))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    existing = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if existing is None:
        return jsonify({"error": "Task not found."}), 404

    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return jsonify({"deleted": task_id})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print(f"Waypoint API starting — database at {DB_PATH}")
    app.run(host="127.0.0.1", port=5000, debug=True)
