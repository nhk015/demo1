# Study Tasks

A lightweight student task manager built with Python, Streamlit, and SQLite. All
task data is stored locally in `tasks.db`, created automatically the first time
the app starts.

## Features

- Add, edit, complete, and delete coursework tasks.
- Browse All, Today, Upcoming, Overdue, and Completed views.
- Search by title and filter by course, priority, and status.
- Sort by due date or priority.
- Track total, completed, overdue, and due-this-week counts.
- See color-coded priority badges and clear overdue alerts.

## Requirements

- Python 3.10 or newer
- pip

## Run locally

From this directory, install the dependency and start Streamlit:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app opens in your browser. The SQLite database is stored beside `app.py`;
keep `tasks.db` to preserve tasks between runs.

## Data and validation

The app uses Python's standard `sqlite3` module directly (no ORM and no separate
backend server). Database values are passed through parameterized SQL
statements. Task titles, priorities, statuses, and due dates are validated
before writes; the database also enforces valid priority and status values.
