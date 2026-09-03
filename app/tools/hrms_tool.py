"""WorkWeek HCM API Integration Tool (FR-3.1 - FR-3.4)."""
import re
import uuid
from datetime import datetime, date
from typing import Dict, Any, Optional

from .. import config

# Synthetic WorkWeek In-Memory Database for MVP 1
EMPLOYEE_DB = {
    "EMP1024": {
        "id": "EMP1024",
        "name": "Alex Tan",
        "title": "Senior Cloud Software Engineer",
        "department": "Solutions Architecture & Engineering",
        "manager_id": "EMP2048",
        "hire_date": "2022-03-15",
        "phone": "+6591234567",
        "address": "12 Marina Boulevard, Marina Bay Financial Centre, Singapore 018982",
        "balances": {
            "vacation": {"accrued": 18.0, "used": 4.0, "remaining": 14.0},
            "sick": {"accrued": 14.0, "used": 2.0, "remaining": 12.0},
        },
        "status": "ACTIVE",
    },
    "EMP2048": {
        "id": "EMP2048",
        "name": "Sarah Chen",
        "title": "Director of Cloud Engineering",
        "department": "Solutions Architecture & Engineering",
        "manager_id": "EMP0001",
        "hire_date": "2019-01-10",
        "phone": "+6598765432",
        "address": "80 Pasir Panjang Road, Mapletree Business City, Singapore 117372",
        "balances": {
            "vacation": {"accrued": 25.0, "used": 5.0, "remaining": 20.0},
            "sick": {"accrued": 14.0, "used": 0.0, "remaining": 14.0},
        },
        "status": "ACTIVE",
    },
}

# Leave Requests Registry
LEAVE_REQUESTS_DB = {}
# Idempotency Cache
IDEMPOTENCY_CACHE = {}


def get_employee_profile(employee_id: str) -> Dict[str, Any]:
    """Retrieve full employee profile metadata from WorkWeek HCM.
    Satisfies BRD: FR-3.2.
    """
    emp = EMPLOYEE_DB.get(employee_id.strip().upper())
    if not emp:
        return {"status_code": 404, "error": f"Employee {employee_id} not found."}
    if emp["status"] != "ACTIVE":
        return {"status_code": 403, "error": f"Employee {employee_id} record is inactive/terminated."}

    return {
        "status_code": 200,
        "employee_id": emp["id"],
        "name": emp["name"],
        "title": emp["title"],
        "department": emp["department"],
        "manager_id": emp["manager_id"],
        "hire_date": emp["hire_date"],
        "phone": emp["phone"],
        "address": emp["address"],
        "origin": config.ORIGIN_HEADER_VALUE,
    }


def get_leave_balances(employee_id: str) -> Dict[str, Any]:
    """Query accrued, used, and remaining leave balances for Vacation and Sick leave.
    Satisfies BRD: FR-3.2.
    """
    emp = EMPLOYEE_DB.get(employee_id.strip().upper())
    if not emp:
        return {"status_code": 404, "error": f"Employee {employee_id} not found."}

    return {
        "status_code": 200,
        "employee_id": emp["id"],
        "vacation_remaining": emp["balances"]["vacation"]["remaining"],
        "vacation_accrued": emp["balances"]["vacation"]["accrued"],
        "sick_remaining": emp["balances"]["sick"]["remaining"],
        "sick_accrued": emp["balances"]["sick"]["accrued"],
        "origin": config.ORIGIN_HEADER_VALUE,
    }


def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    days: float,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a time-off request with operational pre-flight guardrails and balance checks.
    Satisfies BRD: FR-3.3.
    """
    emp_id = employee_id.strip().upper()
    emp = EMPLOYEE_DB.get(emp_id)
    if not emp:
        return {"status_code": 404, "error": f"Employee {employee_id} not found."}

    # Deduplicate via Idempotency Key
    if idempotency_key and idempotency_key in IDEMPOTENCY_CACHE:
        return IDEMPOTENCY_CACHE[idempotency_key]

    # Temporal Validity Guardrails
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"status_code": 400, "error": "Invalid date format. Dates must follow YYYY-MM-DD."}

    if s_date > e_date:
        return {"status_code": 400, "error": "Temporal violation: start_date cannot be later than end_date."}

    norm_type = leave_type.strip().lower()
    if norm_type not in ("sick", "vacation"):
        return {"status_code": 400, "error": f"Unsupported leave type '{leave_type}'. Use 'Sick' or 'Vacation'."}

    # Balance Enforcement Guardrail
    remaining = emp["balances"][norm_type]["remaining"]
    if days > remaining:
        return {
            "status_code": 422,
            "error": "Insufficient balance",
            "message": f"You currently have {remaining} days of accrued {leave_type.capitalize()} leave remaining, but requested {days} days. Would you like to submit a request for {remaining} days instead?",
            "remaining_balance": remaining,
            "deficit": round(days - remaining, 1),
        }

    # Deduct balance and record transaction
    emp["balances"][norm_type]["remaining"] -= days
    emp["balances"][norm_type]["used"] += days

    request_id = f"LOA-{uuid.uuid4().hex[:4].upper()}"
    record = {
        "status_code": 201,
        "request_id": request_id,
        "employee_id": emp_id,
        "leave_type": leave_type.capitalize(),
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "remaining_balance": emp["balances"][norm_type]["remaining"],
        "status": "APPROVED",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "origin": config.ORIGIN_HEADER_VALUE,
    }
    LEAVE_REQUESTS_DB[request_id] = record

    if idempotency_key:
        IDEMPOTENCY_CACHE[idempotency_key] = record

    return record


def update_contact_info(
    employee_id: str,
    phone: Optional[str] = None,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """Update employee contact details (phone / address) with format validation.
    Satisfies BRD: FR-3.2, FR-3.3.
    """
    emp_id = employee_id.strip().upper()
    emp = EMPLOYEE_DB.get(emp_id)
    if not emp:
        return {"status_code": 404, "error": f"Employee {employee_id} not found."}

    if phone:
        phone_clean = phone.strip()
        # E.164 phone pattern check
        if not re.match(r'^\+[1-9]\d{7,14}$', phone_clean):
            return {"status_code": 400, "error": "Invalid phone format. Must follow international E.164 schema (e.g. +6591234567)."}
        emp["phone"] = phone_clean

    if address:
        emp["address"] = address.strip()

    return {
        "status_code": 200,
        "employee_id": emp_id,
        "phone": emp["phone"],
        "address": emp["address"],
        "updated": True,
        "origin": config.ORIGIN_HEADER_VALUE,
    }


def cancel_leave_request(leave_id: str, reason: str = "Compensating transaction") -> Dict[str, Any]:
    """Compensating transaction: cancel a booked leave of absence and refund balance.
    Satisfies BRD: NFR-4.3 (Orchestration Consistency).
    """
    record = LEAVE_REQUESTS_DB.get(leave_id.strip().upper())
    if not record:
        return {"status_code": 404, "error": f"Leave request {leave_id} not found."}

    emp_id = record["employee_id"]
    leave_type = record["leave_type"].lower()
    days = record["days"]

    # Refund balance
    emp = EMPLOYEE_DB[emp_id]
    emp["balances"][leave_type]["remaining"] += days
    emp["balances"][leave_type]["used"] -= days

    record["status"] = "CANCELLED"
    record["cancellation_reason"] = reason

    return {
        "status_code": 200,
        "request_id": leave_id,
        "status": "CANCELLED",
        "refunded_days": days,
        "new_balance": emp["balances"][leave_type]["remaining"],
        "origin": config.ORIGIN_HEADER_VALUE,
    }
