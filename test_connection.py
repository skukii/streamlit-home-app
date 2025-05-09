from sheets_utils import get_sheet, get_worksheet

sheet = get_sheet("HomeSchedulerData")

tasks_ws = get_worksheet(sheet, "Tasks")
shopping_ws = get_worksheet(sheet, "Shopping")

print("✅ Successfully connected!")
print("Tasks headers:", tasks_ws.row_values(1))
print("Shopping headers:", shopping_ws.row_values(1))
