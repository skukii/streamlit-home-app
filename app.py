
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# === FILES ===
TASKS_FILE = "tasks.csv"
LOG_FILE = "log.csv"
SHOPPING_FILE = "shopping.csv"

def load_or_create(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)
    return pd.read_csv(path)

# === Load into session state ===
if "task_df" not in st.session_state:
    st.session_state["task_df"] = load_or_create(TASKS_FILE, ["Task", "Assigned_To", "Done", "Frequency"])
if "log_df" not in st.session_state:
    st.session_state["log_df"] = load_or_create(LOG_FILE, ["Task", "Date_Done", "Assigned_To"])
if "shopping_df" not in st.session_state:
    st.session_state["shopping_df"] = load_or_create(SHOPPING_FILE, ["Item", "Category", "Bought"])

task_df = st.session_state["task_df"]
log_df = st.session_state["log_df"]
shopping_df = st.session_state["shopping_df"]

def save_all():
    st.session_state["task_df"].to_csv(TASKS_FILE, index=False)
    st.session_state["log_df"].to_csv(LOG_FILE, index=False)
    st.session_state["shopping_df"].to_csv(SHOPPING_FILE, index=False)

def get_last_done_date(task):
    logs = log_df[log_df["Task"] == task]
    return pd.to_datetime(logs["Date_Done"]).max().strftime("%Y-%m-%d") if not logs.empty else "Never"

def log_completion(task, assigned):
    new_entry = pd.DataFrame([[task, date.today().strftime("%Y-%m-%d"), assigned]],
                             columns=["Task", "Date_Done", "Assigned_To"])
    st.session_state["log_df"] = pd.concat([log_df, new_entry], ignore_index=True)

def refresh_recurring_tasks():
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    for i, row in task_df.iterrows():
        freq = str(row["Frequency"]).lower()
        task = row["Task"]
        assigned = row["Assigned_To"]
        done = str(row["Done"]).upper()

        if freq in ["once", "daily"]:
            continue

        logs = log_df[log_df["Task"] == task]
        last_done = pd.to_datetime(logs["Date_Done"]).max() if not logs.empty else None

        should_reset = (
            (freq == "weekly" and (not last_done or last_done.date() < start_of_week)) or
            (freq == "monthly" and (not last_done or last_done.date() < start_of_month))
        )

        if should_reset and done == "TRUE":
            st.session_state["task_df"].at[i, "Done"] = "FALSE"

refresh_recurring_tasks()

st.title("🏠 Home Scheduler")

today = date.today()
start_of_week = today - timedelta(days=today.weekday())

st.header("✅ Daily Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "daily"].iterrows():
    task = row["Task"]
    assigned = row["Assigned_To"]
    key = f"daily_{task}_{i}"
    done_today = not log_df[(log_df["Task"] == task) & (log_df["Date_Done"] == today.strftime("%Y-%m-%d"))].empty
    if done_today:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key):
            log_completion(task, assigned)
            st.rerun()

st.header("📆 Weekly Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "weekly"].iterrows():
    task = row["Task"]
    assigned = row["Assigned_To"]
    key = f"weekly_{task}_{i}"
    log_dates = pd.to_datetime(log_df["Date_Done"]).dt.date
    done_this_week = not log_df[(log_df["Task"] == task) & (log_dates >= start_of_week)].empty
    if done_this_week:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key):
            log_completion(task, assigned)
            st.session_state["task_df"].at[i, "Done"] = "TRUE"
            st.rerun()

st.header("📅 Monthly Tasks")
log_dates = pd.to_datetime(log_df["Date_Done"]).dt.date
done_this_month = not log_df[
    (log_df["Task"] == task) &
    (log_dates >= start_of_month)
].empty

for i, row in task_df[task_df["Frequency"].str.lower() == "monthly"].iterrows():
    task = row["Task"]
    assigned = row["Assigned_To"]
    key = f"monthly_{task}_{i}"
    log_dates = pd.to_datetime(log_df["Date_Done"]).dt.date
    done_this_month = not log_df[(log_df["Task"] == task) & (log_dates >= start_of_week)].empty

    if done_this_month:
        st.checkbox(f"~~{task}~~ (Assigned to {assigned}) ✅", value=True, disabled=True, key=key, help=f"Last done: {get_last_done_date(task)}")
    else:
        if st.checkbox(f"{task} (Assigned to {assigned})", key=key):
            log_completion(task, assigned)
            st.session_state["task_df"].at[i, "Done"] = "TRUE"
            st.rerun()

st.header("❌ Missed 'Once' Tasks")
for i, row in task_df[task_df["Frequency"].str.lower() == "once"].iterrows():
    if str(row["Done"]).upper() != "TRUE":
        task = row["Task"]
        assigned = row["Assigned_To"]
        key = f"missed_{task}_{i}"
        if st.checkbox(f"🔔 {task} (Assigned to {assigned}) not done!", key=key):
            st.session_state["task_df"].at[i, "Done"] = "TRUE"
            st.rerun()

st.subheader("➕ Add New Task")
with st.form("add_task_form"):
    new_task = st.text_input("Task")
    new_freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly", "Twice a Month", "Once"])
    new_assigned = st.text_input("Assigned To")
    submitted = st.form_submit_button("Add")
    if submitted and new_task:
        new_row = pd.DataFrame([[new_task, new_assigned, "FALSE", new_freq]], columns=task_df.columns)
        st.session_state["task_df"] = pd.concat([task_df, new_row], ignore_index=True)
        st.success("Task added!")
        st.rerun()

st.header("🛒 Shopping List")
if not shopping_df.empty:
    categories = shopping_df["Category"].unique()
    selected_cat = st.selectbox("Filter by category", ["All"] + list(categories))
    view_df = shopping_df if selected_cat == "All" else shopping_df[shopping_df["Category"] == selected_cat]
else:
    view_df = shopping_df

for i, row in view_df.iterrows():
    item = row["Item"]
    bought = str(row["Bought"]).upper() == "TRUE"
    key = f"shop_{item}_{i}"
    new_state = st.checkbox(item, value=bought, key=key)
    if new_state != bought:
        st.session_state["shopping_df"].at[i, "Bought"] = "TRUE" if new_state else "FALSE"
        st.rerun()

st.markdown("---")
st.subheader("➕ Add Shopping Item")
with st.form("add_item_form"):
    item = st.text_input("Item")
    cat = st.text_input("Category")
    if st.form_submit_button("Add") and item:
        new_row = pd.DataFrame([[item, cat, "FALSE"]], columns=shopping_df.columns)
        st.session_state["shopping_df"] = pd.concat([shopping_df, new_row], ignore_index=True)
        st.success("Item added!")
        st.rerun()

# === Google Sheets Sync ===
def sync_to_google_sheets(sheet_name="HomeSchedulerData"):
    try:
        creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name)

        def upload_df_to_sheet(df, tab):
            try:
                ws = sheet.worksheet(tab)
            except:
                ws = sheet.add_worksheet(title=tab, rows="100", cols="20")
            ws.clear()
            ws.update([df.columns.tolist()] + df.values.tolist())

        upload_df_to_sheet(st.session_state["task_df"], "Tasks")
        upload_df_to_sheet(st.session_state["log_df"], "RecurringLog")
        upload_df_to_sheet(st.session_state["shopping_df"], "Shopping")

        st.success("✅ Google Sheet updated!")
    except Exception as e:
        st.error(f"❌ Failed to sync: {e}")

st.markdown("---")
if st.button("📤 Update Google Sheet"):
    sync_to_google_sheets()
