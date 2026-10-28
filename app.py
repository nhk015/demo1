"""Streamlit interface for a local student task manager."""

from datetime import date, timedelta

import streamlit as st

import db


st.set_page_config(page_title="Study Tasks", page_icon="📚", layout="wide")
db.init_db()


def _parse_due_date(value: object) -> date | None:
    """Parse a stored ISO date, returning None when no date is set."""
    return date.fromisoformat(str(value)) if value else None


def _due_label(value: object) -> str:
    """Format a task due date for display."""
    due = _parse_due_date(value)
    return due.strftime("%b %d, %Y") if due else "No due date"


def _matches_tab(task: dict[str, object], tab_name: str, today: date) -> bool:
    """Apply the date/status rules for one of the task-view tabs."""
    task_status = task["status"]
    due_date = _parse_due_date(task["due_date"])
    if tab_name == "Today":
        return task_status != "Done" and due_date == today
    if tab_name == "Upcoming":
        return task_status != "Done" and due_date is not None and due_date > today
    if tab_name == "Overdue":
        return task_status != "Done" and due_date is not None and due_date < today
    if tab_name == "Completed":
        return task_status == "Done"
    return True


def _sort_tasks(
    tasks: list[dict[str, object]], sort_by: str
) -> list[dict[str, object]]:
    """Sort tasks using stable, explicit keys without interpolating SQL."""
    if sort_by == "Priority":
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        return sorted(
            tasks,
            key=lambda task: (
                priority_order[str(task["priority"])],
                _parse_due_date(task["due_date"]) or date.max,
                int(task["id"]),
            ),
        )
    return sorted(
        tasks,
        key=lambda task: (
            _parse_due_date(task["due_date"]) or date.max,
            int(task["id"]),
        ),
    )


def _render_task(task: dict[str, object], today: date) -> None:
    """Render task details and actions while preserving edit state on reruns."""
    task_id = int(task["id"])
    is_overdue = (
        task["status"] != "Done"
        and _parse_due_date(task["due_date"]) is not None
        and _parse_due_date(task["due_date"]) < today
    )

    with st.container(border=True):
        title_col, badge_col = st.columns([5, 1])
        with title_col:
            st.subheader(str(task["title"]))
        with badge_col:
            st.markdown(
                f'<span class="priority-badge priority-{str(task["priority"]).lower()}">'
                f'{task["priority"]}</span>',
                unsafe_allow_html=True,
            )

        if is_overdue:
            st.warning(f"Overdue · due {_due_label(task['due_date'])}")
        else:
            st.caption(f"Due {_due_label(task['due_date'])}")

        details = []
        if task["course"]:
            details.append(f"**Course:** {task['course']}")
        details.append(f"**Status:** {task['status']}")
        st.markdown(" · ".join(details))
        if task["description"]:
            st.write(task["description"])

        action_cols = st.columns([1, 1, 5])
        if task["status"] != "Done":
            if action_cols[0].button(
                "✓ Mark done", key=f"done_{task_id}", use_container_width=True
            ):
                db.mark_task_done(task_id)
                st.rerun()

        if action_cols[1].button(
            "Edit", key=f"edit_{task_id}", use_container_width=True
        ):
            st.session_state.editing_task_id = task_id
            st.rerun()

        delete_key = f"confirm_delete_{task_id}"
        if action_cols[2].button("Delete", key=f"delete_{task_id}"):
            st.session_state[delete_key] = True
        if st.session_state.get(delete_key):
            st.warning(f"Delete “{task['title']}”? This cannot be undone.")
            confirm_cols = st.columns([1, 1, 5])
            if confirm_cols[0].button(
                "Confirm delete", key=f"confirm_{task_id}", type="primary"
            ):
                db.delete_task(task_id)
                st.session_state.pop(delete_key, None)
                if st.session_state.get("editing_task_id") == task_id:
                    st.session_state.pop("editing_task_id", None)
                st.rerun()
            if confirm_cols[1].button("Cancel", key=f"cancel_{task_id}"):
                st.session_state.pop(delete_key, None)
                st.rerun()

        if st.session_state.get("editing_task_id") == task_id:
            _render_edit_form(task)


def _render_edit_form(task: dict[str, object]) -> None:
    """Show an edit form tied to the selected task ID."""
    task_id = int(task["id"])
    with st.form(f"edit_form_{task_id}"):
        st.markdown("#### Edit task")
        title = st.text_input("Title", value=str(task["title"]), max_chars=200)
        description = st.text_area(
            "Description", value=str(task["description"]), max_chars=2000
        )
        course = st.text_input("Course", value=str(task["course"]), max_chars=100)
        values = list(db.PRIORITIES)
        priority = st.selectbox(
            "Priority", values, index=values.index(str(task["priority"]))
        )
        status_values = list(db.STATUSES)
        status = st.selectbox(
            "Status", status_values, index=status_values.index(str(task["status"]))
        )
        current_due_date = _parse_due_date(task["due_date"])
        due_date = st.date_input(
            "Due date",
            value=current_due_date or date.today(),
            key=f"edit_due_{task_id}",
        )
        no_due_date = st.checkbox(
            "No due date",
            value=current_due_date is None,
            key=f"edit_no_due_{task_id}",
        )
        save_col, cancel_col = st.columns(2)
        submitted = save_col.form_submit_button("Save changes", type="primary")
        cancelled = cancel_col.form_submit_button("Cancel")

    if submitted:
        try:
            db.update_task(
                task_id,
                title,
                description,
                course,
                priority,
                status,
                None if no_due_date else due_date.isoformat(),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state.pop("editing_task_id", None)
            st.rerun()
    if cancelled:
        st.session_state.pop("editing_task_id", None)
        st.rerun()


st.markdown(
    """
    <style>
    .priority-badge {
        display: inline-block;
        border-radius: 999px;
        padding: 0.25rem 0.7rem;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .priority-high { background: #fee2e2; color: #991b1b; }
    .priority-medium { background: #fef3c7; color: #92400e; }
    .priority-low { background: #dcfce7; color: #166534; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📚 Study Tasks")
st.caption("A simple, local-first planner for keeping coursework on track.")

with st.sidebar:
    st.header("Add a task")
    with st.form("add_task_form"):
        new_title = st.text_input("Title *", max_chars=200)
        new_course = st.text_input("Course", max_chars=100)
        new_description = st.text_area("Description", max_chars=2000)
        new_priority = st.selectbox("Priority", db.PRIORITIES, index=1)
        new_due_date = st.date_input("Due date", value=None)
        no_due_date = st.checkbox("No due date")
        add_submitted = st.form_submit_button("Add task", type="primary")

    if add_submitted:
        try:
            db.add_task(
                new_title,
                new_description,
                new_course,
                new_priority,
                None if no_due_date or new_due_date is None else new_due_date.isoformat(),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("Task added.")
            st.rerun()

tasks = db.get_tasks()
today = date.today()
week_end = today + timedelta(days=6 - today.weekday())
completed_tasks = [task for task in tasks if task["status"] == "Done"]
overdue_tasks = [
    task
    for task in tasks
    if task["status"] != "Done"
    and _parse_due_date(task["due_date"]) is not None
    and _parse_due_date(task["due_date"]) < today
]
due_this_week = [
    task
    for task in tasks
    if task["status"] != "Done"
    and _parse_due_date(task["due_date"]) is not None
    and today <= _parse_due_date(task["due_date"]) <= week_end
]

metric_cols = st.columns(4)
metric_cols[0].metric("Total tasks", len(tasks))
metric_cols[1].metric("Completed", len(completed_tasks))
metric_cols[2].metric("Overdue", len(overdue_tasks))
metric_cols[3].metric("Due this week", len(due_this_week))

st.divider()
filter_cols = st.columns([2, 1, 1, 1, 1])
search = filter_cols[0].text_input("Search title", placeholder="Find a task...")
courses = sorted({str(task["course"]) for task in tasks if task["course"]})
course_filter = filter_cols[1].selectbox("Course", ["All courses", *courses])
priority_filter = filter_cols[2].selectbox(
    "Priority", ["All priorities", *db.PRIORITIES]
)
status_filter = filter_cols[3].selectbox("Status", ["All statuses", *db.STATUSES])
sort_by = filter_cols[4].selectbox("Sort by", ["Due date", "Priority"])

filtered_tasks = [
    task
    for task in tasks
    if search.strip().casefold() in str(task["title"]).casefold()
    and (course_filter == "All courses" or task["course"] == course_filter)
    and (
        priority_filter == "All priorities" or task["priority"] == priority_filter
    )
    and (status_filter == "All statuses" or task["status"] == status_filter)
]
filtered_tasks = _sort_tasks(filtered_tasks, sort_by)

tab_names = ("All", "Today", "Upcoming", "Overdue", "Completed")
tabs = st.tabs(tab_names)
for tab, tab_name in zip(tabs, tab_names):
    with tab:
        shown_tasks = [
            task
            for task in filtered_tasks
            if _matches_tab(task, tab_name, today)
        ]
        if not shown_tasks:
            st.info("No tasks match this view yet.")
        for task in shown_tasks:
            _render_task(task, today)
