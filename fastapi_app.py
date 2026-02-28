from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/execute")
def execute_query(q: str = Query(..., description="The query to process")):
    # 1. Ticket Status
    match = re.search(r"What is the status of ticket (\d+)\?", q, re.IGNORECASE)
    if match:
        return {
            "name": "get_ticket_status",
            "arguments": json.dumps({"ticket_id": int(match.group(1))})
        }
        
    # 2. Meeting Scheduling
    match = re.search(r"Schedule a meeting on ([\d-]+) at ([\d:]+) in (.*)\.", q, re.IGNORECASE)
    if match:
        return {
            "name": "schedule_meeting",
            "arguments": json.dumps({
                "date": match.group(1),
                "time": match.group(2),
                "meeting_room": match.group(3).strip()
            })
        }
        
    # 3. Expense Reimbursement
    match = re.search(r"Show my expense balance for employee (\d+)\.", q, re.IGNORECASE)
    if match:
        return {
            "name": "get_expense_balance",
            "arguments": json.dumps({"employee_id": int(match.group(1))})
        }
        
    # 4. Performance Bonus Calculation
    match = re.search(r"Calculate performance bonus for employee (\d+) for (\d+)\.", q, re.IGNORECASE)
    if match:
        return {
            "name": "calculate_performance_bonus",
            "arguments": json.dumps({
                "employee_id": int(match.group(1)),
                "current_year": int(match.group(2))
            })
        }
        
    # 5. Office Issue Reporting
    match = re.search(r"Report office issue (\d+) for the (.*) department\.", q, re.IGNORECASE)
    if match:
        return {
            "name": "report_office_issue",
            "arguments": json.dumps({
                "issue_code": int(match.group(1)),
                "department": match.group(2).strip()
            })
        }
        
    # Fallback
    return {"error": "No matching function found"}
