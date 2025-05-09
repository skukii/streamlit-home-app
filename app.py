import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os

# === FILE PATHS ===
TASKS_FILE = "tasks.csv"
LOG_FILE = "log.csv"
SHOPPING_FILE = "shopping.csv"

# === HELPERS ===
def load_csv(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    return pd.read_csv(path)

def save_csv(df, path):
    df.to_csv(path, index=False)

# === LOAD DATA ===
task_df = load_csv(TASKS_FILE, ["Task", "Assigned_To", "Done", "Frequency"])
log_df = load_csv(LOG_FILE, ["Task", "Date_Done", "Assigned_To"])
shopping_df = load_csv(SHOPPING_FILE, ["Item", "Category", "Bought"])

# === UTILITY ===
def get_last_done_date(task_name):
    task_logs = log_df[log_df["Task"] == task_name]
    if task_logs.empty:
        return "Never"
    return pd.to_datetime(task_logs["Date_Done"]).max().strftime("%Y-%m-%d")

def log_completion(task_name, assigned):
    global log_df
    today_str = date.today().strftime("%Y-%m-%d")
    log_df = pd.concat([log_df, pd.DataFrame([{
        "Task": task_name, "Date_Done": today_str, "Assigned_To": assigned
    }])], ignore_index=True)
    save_csv(log_df, LOG_FILE)

def refresh_recurring_tasks():
    global task_df
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    for i, row in task_df.iterrows():
        freq = str(row["Frequency"]).lower()
        task = row["Task"]
        assigned = row["Assigned_To"]
        done = row["Done"].upper()

        if freq in ["once", "daily"]:
            continue

        task_logs = log_df[log_df["Task"] == task]
        last_done = pd.to_datetime(task_logs["Date_Done"]).max() if not task_logs.empty else None

        should_reset = False
        if freq == "weekly" and (not last_done or last_done.date() < start_of_week):
            should_reset = True
        elif freq == "monthly" and (not last_done or last_done.date() < start_of_month):
            should_reset = True

        if should_reset and done == "TRUE":
            task_df.at[i, "Done"] = "FALSE"

    save_csv(task_df, TASKS_FILE)

refresh_recurring_tasks()

# === DATES ===
today = date.today()
start_of_week = today - timedelta(days=today.weekday())
end_of_week = start_of_week + timedelta(days=6)

# === UI ===
st.title("🏠 Home Scheduler")

# === TASKS ===
st.header("✅ Daily Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "daily"].iterrows():
    task, assigned = row["Task"], row["Assigned_To"]
    done_today = not log_df[(log_df["Task"] == task) & (log_df["Date_Done"] == today.strftime("%Y-%m-%d"))].empty
    key = f"daily_{task}_{i}"
    if done_today:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key):
            log_completion(task, assigned)
            st.rerun()

st.header("📆 Weekly Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "weekly"].iterrows():
    task, assigned = row["Task"], row["Assigned_To"]
    done_this_week = not log_df[(log_df["Task"] == task) & (pd.to_datetime(log_df["Date_Done"]) >= start_of_week)].empty
    key = f"weekly_{task}_{i}"
    if done_this_week:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key, help=f"Last done: {get_last_done_date(task)}"):
            log_completion(task, assigned)
            task_df.at[i, "Done"] = "TRUE"
            save_csv(task_df, TASKS_FILE)
            st.rerun()

st.header("📅 Monthly Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "monthly"].iterrows():
    task, assigned = row["Task"], row["Assigned_To"]
    this_month = pd.to_datetime(log_df["Date_Done"]).dt.month == today.month
    done_this_month = not log_df[(log_df["Task"] == task) & this_month].empty
    key = f"monthly_{task}_{i}"
    if done_this_month:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key, help=f"Last done: {get_last_done_date(task)}"):
            log_completion(task, assigned)
            task_df.at[i, "Done"] = "TRUE"
            save_csv(task_df, TASKS_FILE)
            st.rerun()

st.header("❌ Missed 'Once' Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "once"].iterrows():
    if row["Done"].upper() != "TRUE":
        task, assigned = row["Task"], row["Assigned_To"]
        key = f"missed_{task}_{i}"
        if st.checkbox(f"🔔 {task} (Assigned to {assigned}) not done!", key=key):
            task_df.at[i, "Done"] = "TRUE"
            save_csv(task_df, TASKS_FILE)
            st.rerun()

st.header("➕ Add New Task")
with st.form("add_task_form"):
    new_task = st.text_input("Task")
    new_freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Twice a Month", "Once"])
    new_assigned = st.text_input("Assigned To")
    submitted = st.form_submit_button("Add")
    if submitted and new_task:
        new_row = pd.DataFrame([[new_task, new_assigned, "FALSE", new_freq]], columns=task_df.columns)
        task_df = pd.concat([task_df, new_row], ignore_index=True)
        save_csv(task_df, TASKS_FILE)
        st.success("Task added!")
        st.rerun()

# === SHOPPING ===
st.header("🛒 Shopping List")

if not shopping_df.empty:
    categories = shopping_df["Category"].unique()
    selected_cat = st.selectbox("Filter by category", ["All"] + list(categories))
    view_df = shopping_df if selected_cat == "All" else shopping_df[shopping_df["Category"] == selected_cat]
else:
    view_df = shopping_df

for i, row in view_df.iterrows():
    item = row["Item"]
    bought = row["Bought"] == "TRUE"
    key = f"shop_{item}_{i}"
    new_state = st.checkbox(item, value=bought, key=key)
    if new_state != bought:
        shopping_df.at[i, "Bought"] = "TRUE" if new_state else "FALSE"
        save_csv(shopping_df, SHOPPING_FILE)
        st.rerun()

st.markdown("---")
st.subheader("➕ Add Shopping Item")
with st.form("add_item_form"):
    item = st.text_input("Item")
    cat = st.text_input("Category")
    if st.form_submit_button("Add") and item:
        new_row = pd.DataFrame([[item, cat, "FALSE"]], columns=shopping_df.columns)
        shopping_df = pd.concat([shopping_df, new_row], ignore_index=True)
        save_csv(shopping_df, SHOPPING_FILE)
        st.success("Item added!")
        st.rerun()
