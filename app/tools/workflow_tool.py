"""Cross-System Orchestration Flow Tool (UC-2.2 Medical Leave & Delegation)."""
from typing import Dict, Any, Optional

from . import hrms_tool
from . import itms_tool


def execute_medical_leave_workflow(
    employee_id: str,
    start_date: str,
    end_date: str,
    days: float,
    simulate_ticket_failure: bool = False,
) -> Dict[str, Any]:
    """Execute cross-system medical leave submission with automatic IT delegation ticket
    and distributed compensation if Step 2 fails.
    Satisfies BRD: UC-2.2, NFR-4.3.
    """
    emp_id = employee_id.strip().upper()

    # Step 1: Pre-flight balance check
    bal = hrms_tool.get_leave_balances(emp_id)
    if bal.get("status_code") != 200:
        return {"success": False, "step": "balance_check", "error": bal.get("error")}

    sick_remaining = bal.get("sick_remaining", 0)
    if days > sick_remaining:
        return {
            "success": False,
            "step": "balance_validation",
            "error": f"Insufficient sick leave balance. You requested {days} days, but only {sick_remaining} days are available.",
            "remaining_balance": sick_remaining,
        }

    # Step 2: Book leave in WorkWeek
    loa_result = hrms_tool.submit_leave_request(
        employee_id=emp_id,
        leave_type="Sick",
        start_date=start_date,
        end_date=end_date,
        days=days,
    )
    if loa_result.get("status_code") != 201:
        return {"success": False, "step": "workweek_submission", "error": loa_result.get("error")}

    loa_id = loa_result["request_id"]

    # Step 3: Create Out-of-Office Email Delegation ticket in ServiceImmediately
    if simulate_ticket_failure:
        ticket_result = {"status_code": 503, "error": "Simulated ServiceImmediately backend outage"}
    else:
        ticket_result = itms_tool.create_incident_ticket(
            caller_id=emp_id,
            category="HRSD",
            short_desc=f"Out-of-Office Email Delegation during {loa_id}",
            priority="3 - Moderate",
        )

    # Step 4: Check for Partial Failure and Execute Compensation if needed
    if ticket_result.get("status_code") != 201:
        # Step 2 succeeded but Step 3 failed -> Trigger compensation
        compensation = hrms_tool.cancel_leave_request(
            leave_id=loa_id,
            reason="Compensating transaction: ServiceImmediately ticket creation failed.",
        )
        return {
            "success": False,
            "step": "itms_ticket_creation",
            "error": ticket_result.get("error"),
            "compensation_executed": True,
            "compensation_status": compensation.get("status"),
            "refunded_days": compensation.get("refunded_days"),
            "message": f"Your medical leave request was rolled back because the IT delegation ticket could not be created. Balance has been restored.",
        }

    ticket_id = ticket_result["ticket_id"]

    # Step 5: Success Synthesis
    return {
        "success": True,
        "employee_id": emp_id,
        "leave_request_id": loa_id,
        "incident_ticket_id": ticket_id,
        "leave_type": "Sick",
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "message": f"Your medical leave request #{loa_id} has been submitted successfully in WorkWeek ({days} days deducted). Your out-of-office delegation ticket #{ticket_id} has been opened in ServiceImmediately.",
    }
