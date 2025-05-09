import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, timedelta
import calendar
import json
import streamlit as st



SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_sheet(sheet_name="HomeSchedulerData"):
    creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    return client.open(sheet_name)

def get_worksheet(sheet, name):
    try:
        return sheet.worksheet(name)
    except:
        return sheet.add_worksheet(title=name, rows="100", cols="20")

def log_recurring_completion(task_name, assigned, date_str):
    log_ws = get_worksheet(get_sheet(), "RecurringLog")
    log_ws.append_row([task_name, date_str, assigned])

def get_last_done_date(task_name):
    log_ws = get_worksheet(get_sheet(), "RecurringLog")
    records = log_ws.get_all_records()
    relevant = [r for r in records if r["Task"] == task_name]
    if not relevant:
        return "Never"
    last_done = max(datetime.strptime(r["Date Done"], "%Y-%m-%d") for r in relevant)
    return last_done.strftime("%Y-%m-%d")

def task_already_exists(task_name, assigned):
    task_ws = get_worksheet(get_sheet(), "Tasks")
    records = task_ws.get_all_records()
    for row in records:
        if row["Task"] == task_name and row["Assigned To"] == assigned:
            return True
    return False

def refresh_recurring_tasks():
    task_ws = get_worksheet(get_sheet(), "Tasks")
    log_ws = get_worksheet(get_sheet(), "RecurringLog")
    task_records = task_ws.get_all_records()
    log_records = log_ws.get_all_records()

    today = datetime.today().date()
    weekday = today.weekday()
    start_of_week = today - timedelta(days=weekday)
    start_of_month = date(today.year, today.month, 1)

    updated_rows = []

    for idx, row in enumerate(task_records):
        freq = row.get("Frequency", "once").lower()
        task_name = row["Task"]
        assigned = row["Assigned To"]
        done_flag = row.get("Done", "FALSE").upper()

        if freq == "once" or freq == "daily":
            continue

        relevant = [r for r in log_records if r["Task"] == task_name]
        last_done = max([datetime.strptime(r["Date Done"], "%Y-%m-%d").date() for r in relevant], default=None) if relevant else None

        if freq == "weekly":
            if last_done is None or last_done < start_of_week:
                if done_flag == "TRUE":
                    task_ws.update_cell(idx + 2, 3, "FALSE")
        elif freq == "monthly":
            if last_done is None or last_done < start_of_month:
                if done_flag == "TRUE":
                    task_ws.update_cell(idx + 2, 3, "FALSE")
