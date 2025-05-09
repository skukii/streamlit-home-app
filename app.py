#streamlit run app.py
import streamlit as st
st.set_page_config(page_title="Home Scheduler", layout="wide")
from datetime import datetime, date, timedelta
import pandas as pd
import calendar as cal
from streamlit_calendar import calendar

from sheets_utils import (
    get_sheet,
    get_worksheet,
    task_already_exists,
    log_recurring_completion,
    get_last_done_date,
    refresh_recurring_tasks
)

@st.cache_data(ttl=300)
def load_data():
    sheet = get_sheet("HomeSchedulerData")
    task_ws = get_worksheet(sheet, "Tasks")
    log_ws = get_worksheet(sheet, "RecurringLog")
    task_df = pd.DataFrame(task_ws.get_all_records())
    done_df = pd.DataFrame(log_ws.get_all_records())
    return sheet, task_ws, log_ws, task_df, done_df

refresh_recurring_tasks()
sheet, task_ws, log_ws, task_df, done_df = load_data()

if not task_df.empty:
    task_df["Done"] = task_df["Done"].astype(str).str.upper()
if not done_df.empty:
    done_df["Date Done"] = pd.to_datetime(done_df["Date Done"]).dt.date

today = date.today()
start_of_week = today - timedelta(days=today.weekday())
end_of_week = start_of_week + timedelta(days=6)
start_of_month = date(today.year, today.month, 1)
end_of_month = date(today.year, today.month, cal.monthrange(today.year, today.month)[1])


custom_css = """
<style>
.fc .fc-toolbar-title {
    font-size: 1.3rem !important;
    color: #ffffff;
}
.fc .fc-button {
    background-color: #444;
    border: none;
    border-radius: 6px;
    padding: 0.25rem 0.75rem;
    margin: 2px;
    color: #eee;
    font-size: 0.9rem;
}
.fc .fc-button:hover {
    background-color: #666;
}
.fc .fc-daygrid-day-number {
    color: #eee;
}
.fc .fc-daygrid-day.fc-day-today {
    background-color: rgba(255, 99, 132, 0.2) !important;
    border-radius: 8px;
}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)
st.title("\U0001F3E1 Home Scheduler")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("\u2705 Daily Tasks")
    daily_tasks = task_df[task_df["Frequency"].str.lower() == "daily"]
    for i, row in daily_tasks.iterrows():
        task_name = row["Task"]
        assigned = row["Assigned To"]
        key = f"daily_{task_name}_{i}"
        done_today = not done_df[(done_df["Task"] == task_name) & (done_df["Date Done"] == today)].empty
        if done_today:
            last_done = get_last_done_date(task_name)
            st.checkbox(f"~~{task_name}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {last_done}")
        else:
            st.checkbox(f"{task_name} (Assigned to {assigned})", value=False, key=key)

    st.subheader("\U0001F4C6 Weekly Tasks")
    weekly_tasks = task_df[task_df["Frequency"].str.lower() == "weekly"]
    for i, row in weekly_tasks.iterrows():
        task_name = row["Task"]
        assigned = row["Assigned To"]
        key = f"weekly_{task_name}_{i}"
        recent_dones = done_df[(done_df["Task"] == task_name) & (done_df["Date Done"] >= start_of_week)]
        last_done = get_last_done_date(task_name)
        if not recent_dones.empty:
            st.checkbox(f"~~{task_name}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {last_done}")
        else:
            st.checkbox(f"{task_name} (Assigned to {assigned})", value=False, key=key, help=f"Last done: {last_done}")

    st.subheader("\U0001F4C5 Monthly Tasks")
    monthly_tasks = task_df[task_df["Frequency"].str.lower() == "monthly"]
    for i, row in monthly_tasks.iterrows():
        task_name = row["Task"]
        assigned = row["Assigned To"]
        key = f"monthly_{task_name}_{i}"
        recent_dones = done_df[(done_df["Task"] == task_name) & (done_df["Date Done"].dt.month == today.month) & (done_df["Date Done"].dt.year == today.year)]
        last_done = get_last_done_date(task_name)
        if not recent_dones.empty:
            st.checkbox(f"~~{task_name}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {last_done}")
        else:
            st.checkbox(f"{task_name} (Assigned to {assigned})", value=False, key=key, help=f"Last done: {last_done}")

    st.subheader("\u274C Missed Tasks")
    once_tasks = task_df[task_df["Frequency"].str.lower() == "once"]
    for i, row in once_tasks.iterrows():
        if row["Done"] != "TRUE":
            task_name = row["Task"]
            assigned = row["Assigned To"]
            key = f"missed_{task_name}_{i}"
            st.checkbox(f"\U0001F514 {task_name} (Assigned to {assigned}) not done!", value=False, key=key)

    st.subheader("\u2795 Add New Task")
    with st.form("new_task"):
        new_task = st.text_input("Task")
        frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Twice a Month", "Once"])
        assigned_to = st.text_input("Assigned To")
        submitted = st.form_submit_button("Add Task")

        if submitted and new_task:
            task_ws.append_row([new_task, assigned_to, "FALSE", frequency])
            st.success("Task added!")
            st.rerun()

with col2:
    st.subheader("\U0001F4C5 Calendar")
    calendar(
        options={
            "initialView": "dayGridMonth",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay"
            },
            "height": 600,
            "weekends": True,
            "nowIndicator": True,
            "selectable": True
        },
        key="calendar"
    )
