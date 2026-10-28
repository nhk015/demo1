"""SQLite persistence and validation for the student task manager."""

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
import sqlite3
from typing import Iterator


DB_PATH = Path(__file__).with_name("tasks.db")
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("To Do", "In Progress", "Done")


@contextmanager
def _connection(db_path: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open a database connection and commit successful operations."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _validate_task(
    title: str,
    priority: str,
    due_date: str | None,
    status: str | None = None,
) -> tuple[str, str | None]:
    """Validate and normalize values shared by task creation and updates."""
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("A task title is required.")
    if len(clean_title) > 200:
        raise ValueError("Task titles must be 200 characters or fewer.")
    if priority not in PRIORITIES:
        raise ValueError("Priority must be Low, Medium, or High.")
    if status is not None and status not in STATUSES:
        raise ValueError("Status must be To Do, In Progress, or Done.")

    clean_due_date = due_date.strip() if due_date else None
    if clean_due_date:
        try:
            parsed_due_date = date.fromisoformat(clean_due_date)
        except ValueError as exc:
            raise ValueError("Due date must be a valid calendar date.") from exc
        if parsed_due_date.isoformat() != clean_due_date:
            raise ValueError("Due date must use YYYY-MM-DD format.")

    return clean_title, clean_due_date


def init_db(db_path: str | Path = DB_PATH) -> None:
    """Create the tasks table and indexes if they do not already exist."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                description TEXT NOT NULL DEFAULT '',
                course TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
                status TEXT NOT NULL DEFAULT 'To Do'
                    CHECK(status IN ('To Do', 'In Progress', 'Done')),
                due_date TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_due_date "
            "ON tasks(status, due_date)"
        )


def add_task(
    title: str,
    description: str = "",
    course: str = "",
    priority: str = "Medium",
    due_date: str | None = None,
    db_path: str | Path = DB_PATH,
) -> int:
    """Validate and insert a task, returning its new ID."""
    clean_title, clean_due_date = _validate_task(title, priority, due_date)
    if len(description) > 2000:
        raise ValueError("Descriptions must be 2,000 characters or fewer.")
    if len(course) > 100:
        raise ValueError("Course names must be 100 characters or fewer.")

    created_at = datetime.now().isoformat(timespec="seconds")
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks
                (title, description, course, priority, status, due_date, created_at)
            VALUES (?, ?, ?, ?, 'To Do', ?, ?)
            """,
            (
                clean_title,
                description.strip(),
                course.strip(),
                priority,
                clean_due_date,
                created_at,
            ),
        )
        return int(cursor.lastrowid)


def get_tasks(db_path: str | Path = DB_PATH) -> list[dict[str, object]]:
    """Return all tasks, with newest tasks first when due dates match."""
    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, description, course, priority, status,
                   due_date, created_at, completed_at
            FROM tasks
            ORDER BY
                CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                due_date ASC,
                created_at DESC,
                id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def update_task(
    task_id: int,
    title: str,
    description: str,
    course: str,
    priority: str,
    status: str,
    due_date: str | None,
    db_path: str | Path = DB_PATH,
) -> None:
    """Validate and update task details and completion metadata."""
    clean_title, clean_due_date = _validate_task(title, priority, due_date, status)
    if len(description) > 2000:
        raise ValueError("Descriptions must be 2,000 characters or fewer.")
    if len(course) > 100:
        raise ValueError("Course names must be 100 characters or fewer.")

    completed_at = datetime.now().isoformat(timespec="seconds")
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, course = ?, priority = ?, status = ?,
                due_date = ?,
                completed_at = CASE
                    WHEN ? = 'Done' THEN COALESCE(completed_at, ?)
                    ELSE NULL
                END
            WHERE id = ?
            """,
            (
                clean_title,
                description.strip(),
                course.strip(),
                priority,
                status,
                clean_due_date,
                status,
                completed_at,
                task_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError("Task was not found.")


def mark_task_done(task_id: int, db_path: str | Path = DB_PATH) -> None:
    """Mark a task complete and record when it was completed."""
    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = 'Done', completed_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(timespec="seconds"), task_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("Task was not found.")


def delete_task(task_id: int, db_path: str | Path = DB_PATH) -> None:
    """Delete a task by ID."""
    with _connection(db_path) as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise ValueError("Task was not found.")
