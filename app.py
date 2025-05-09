import duckdb
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import streamlit as st

DB_PATH = "scheduler.duckdb"

# Ensure tables exist
@st.cache_resource
def initialize_db():
    with duckdb.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS Tasks (
            Task TEXT,
            Assigned_To TEXT,
            Done TEXT,
            Frequency TEXT
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS RecurringLog (
            Task TEXT,
            Date_Done TEXT,
            Assigned_To TEXT
        )
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS Shopping (
            Item TEXT,
            Category TEXT,
            Bought TEXT
        )
        """)
    return DB_PATH

db_path = initialize_db()

def get_tasks():
    with duckdb.connect(db_path) as con:
        return con.execute("SELECT * FROM Tasks").df()

def get_log():
    with duckdb.connect(db_path) as con:
        return con.execute("SELECT * FROM RecurringLog").df()

def get_shopping():
    with duckdb.connect(db_path) as con:
        return con.execute("SELECT * FROM Shopping").df()

def add_shopping_item(item, category):
    with duckdb.connect(db_path) as con:
        con.execute("INSERT INTO Shopping VALUES (?, ?, 'FALSE')", (item, category))

def update_shopping_status(item, status):
    with duckdb.connect(db_path) as con:
        con.execute("UPDATE Shopping SET Bought = ? WHERE Item = ?", (status, item))

def log_recurring_completion(task_name, assigned, date_str):
    with duckdb.connect(db_path) as con:
        con.execute("INSERT INTO RecurringLog VALUES (?, ?, ?)", (task_name, date_str, assigned))

def get_last_done_date(task_name):
    with duckdb.connect(db_path) as con:
        df = con.execute("SELECT Date_Done FROM RecurringLog WHERE Task = ?", (task_name,)).df()
        if df.empty:
            return "Never"
        return max(pd.to_datetime(df["Date_Done"])).strftime("%Y-%m-%d")

def task_already_exists(task_name, assigned):
    with duckdb.connect(db_path) as con:
        result = con.execute("""
            SELECT * FROM Tasks
            WHERE Task = ? AND Assigned_To = ?
        """, (task_name, assigned)).fetchone()
        return result is not None

def refresh_recurring_tasks():
    try:
        task_df = get_tasks()
        log_df = get_log()
    except Exception as e:
        st.warning("DuckDB read error. Skipping refresh.")
        return

    today = datetime.today().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = date(today.year, today.month, 1)

    with duckdb.connect(db_path) as con:
        for idx, row in task_df.iterrows():
            freq = row.get("Frequency", "once").lower()
            task_name = row["Task"]
            assigned = row["Assigned_To"]
            done_flag = row.get("Done", "FALSE").upper()

            if freq in ["once", "daily"]:
                continue

            relevant = log_df[log_df["Task"] == task_name]
            if relevant.empty:
                last_done = None
            else:
                last_done = max(pd.to_datetime(relevant["Date_Done"]))

            reset = False
            if freq == "weekly" and (last_done is None or last_done.date() < start_of_week):
                reset = True
            elif freq == "monthly" and (last_done is None or last_done.date() < start_of_month):
                reset = True

            if reset and done_flag == "TRUE":
                con.execute("""
                    UPDATE Tasks SET Done = 'FALSE'
                    WHERE Task = ? AND Assigned_To = ?
                """, (task_name, assigned))

# UI integration for shopping list
if "Shopping" not in st.session_state:
    st.session_state["Shopping"] = get_shopping()

st.subheader("🛒 Shopping List")
shopping_df = st.session_state["Shopping"]

categories = shopping_df["Category"].unique() if not shopping_df.empty else []
selected_category = st.selectbox("Filter by category", ["All"] + list(categories))

filtered_shopping = shopping_df if selected_category == "All" else shopping_df[shopping_df["Category"] == selected_category]

for i, row in filtered_shopping.iterrows():
    item = row["Item"]
    bought = row["Bought"] == "TRUE"
    key = f"shop_{item}_{i}"
    new_state = st.checkbox(f"{item}", value=bought, key=key)
    if new_state != bought:
        update_shopping_status(item, "TRUE" if new_state else "FALSE")
        st.session_state["Shopping"] = get_shopping()
        st.experimental_rerun()

st.markdown("---")
st.markdown("**Add New Item**")
with st.form("add_shopping"):
    new_item = st.text_input("Item")
    category = st.text_input("Category")
    submitted = st.form_submit_button("Add")
    if submitted and new_item:
        add_shopping_item(new_item, category)
        st.success("Item added!")
        st.session_state["Shopping"] = get_shopping()
        st.experimental_rerun()
