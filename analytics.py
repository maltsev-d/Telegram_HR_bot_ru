import csv
import os

CSV_FILE = "data/analytics.csv"

FIELDNAMES = ["user_id", "full_name", "username", "date", "status",
    "vacancy", "important", "salary_expectations", "interview_date",
    "desired_interview_time", "reason", "refusal_reason",
    "final_rejection_reason"]



def init_analytics():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

async def update_user_fields(user_id, **fields):
    updated = False
    data = []

    if not os.path.exists(CSV_FILE):
        init_analytics()

    with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["user_id"] == str(user_id):
                row.update(fields)
                updated = True
            data.append(row)

    if not updated:
        row = {"user_id": str(user_id)}
        row.update(fields)
        data.append(row)

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)