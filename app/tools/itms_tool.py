"""ServiceImmediately ITSM Integration Tool (FR-4.1 - FR-4.3)."""
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .. import config

# Lifecycle States in ServiceImmediately
STATE_MAP = {
    1: "New",
    2: "In Progress",
    3: "On Hold",
    6: "Resolved",
    7: "Closed",
}

# Synthetic Tickets Database
TICKETS_DB = {
    "INC-55100": {
        "id": "INC-55100",
        "caller_id": "EMP1024",
        "category": "Hardware",
        "short_description": "Laptop screen flickering intermittently",
        "priority": "3 - Moderate",
        "state": 2,
        "state_label": "In Progress",
        "assignee": "IT Support Desk",
        "created_at": "2026-09-01T08:00:00Z",
        "comments": [
            {"time": "2026-09-01T08:05:00Z", "author": "System", "text": "Ticket auto-routed to Tier 1."},
            {"time": "2026-09-01T10:15:00Z", "author": "IT Tech", "text": "Hardware diagnostics scheduled."},
        ],
        "close_notes": None,
        "origin": config.ORIGIN_HEADER_VALUE,
    }
}

# Duplicate Prevention History (tracks: caller_id + short_desc -> timestamp)
RECENT_SUBMISSIONS = {}
IDEMPOTENCY_CACHE = {}


def get_incident_ticket(ticket_id: str) -> Dict[str, Any]:
    """Retrieve ticket details, state, priority, and activity timeline.
    Satisfies BRD: FR-4.2.
    """
    tid = ticket_id.strip().upper()
    ticket = TICKETS_DB.get(tid)
    if not ticket:
        return {"status_code": 404, "error": f"Incident ticket '{ticket_id}' not found."}

    return {
        "status_code": 200,
        "ticket_id": ticket["id"],
        "caller_id": ticket["caller_id"],
        "category": ticket["category"],
        "short_description": ticket["short_description"],
        "priority": ticket["priority"],
        "state": ticket["state"],
        "state_label": ticket["state_label"],
        "assignee": ticket["assignee"],
        "created_at": ticket["created_at"],
        "comments": ticket["comments"],
        "close_notes": ticket["close_notes"],
        "origin": config.ORIGIN_HEADER_VALUE,
    }


def create_incident_ticket(
    caller_id: str,
    category: str,
    short_desc: str,
    priority: str = "3 - Moderate",
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new support incident ticket in ServiceImmediately.
    Enforces duplicate suppression and priority alignment guardrails.
    Satisfies BRD: FR-4.2, FR-4.3.
    """
    c_id = caller_id.strip().upper()
    s_desc = short_desc.strip()

    # Idempotency Deduplication
    if idempotency_key and idempotency_key in IDEMPOTENCY_CACHE:
        return IDEMPOTENCY_CACHE[idempotency_key]

    # Duplicate Mitigation: Check for duplicate submissions in the last 15 minutes (900s)
    dup_key = f"{c_id}:{s_desc.lower()}"
    now = time.time()
    if dup_key in RECENT_SUBMISSIONS and (now - RECENT_SUBMISSIONS[dup_key] < 900):
        return {
            "status_code": 409,
            "error": "Duplicate ticket mitigation: A ticket with identical summary was submitted in the last 15 minutes.",
        }

    # Priority Verification Guardrail
    valid_priorities = ("1 - Critical", "2 - High", "3 - Moderate", "4 - Low")
    if priority not in valid_priorities:
        return {"status_code": 400, "error": f"Invalid priority '{priority}'. Must be one of: {valid_priorities}."}

    if priority == "1 - Critical":
        critical_keywords = ("outage", "production down", "p0", "company-wide", "security breach")
        if not any(k in s_desc.lower() for k in critical_keywords):
            return {
                "status_code": 400,
                "error": "Priority violation: '1 - Critical' requires documented production outage or company-wide disruption.",
            }

    ticket_id = f"INC-{uuid.uuid4().hex[:5].upper()}"
    record = {
        "status_code": 201,
        "ticket_id": ticket_id,
        "caller_id": c_id,
        "category": category.strip(),
        "short_description": s_desc,
        "priority": priority,
        "state": 1,
        "state_label": "New",
        "assignee": "HRSD Triage Desk",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "comments": [
            {"time": datetime.utcnow().isoformat() + "Z", "author": "Automation Agent", "text": "Incident logged via Altostrat HR Agent."}
        ],
        "close_notes": None,
        "origin": config.ORIGIN_HEADER_VALUE,
    }

    TICKETS_DB[ticket_id] = record
    RECENT_SUBMISSIONS[dup_key] = now

    if idempotency_key:
        IDEMPOTENCY_CACHE[idempotency_key] = record

    return record


def add_ticket_comment(ticket_id: str, comment: str) -> Dict[str, Any]:
    """Append notes or comments to the incident activity stream.
    Satisfies BRD: FR-4.2.
    """
    tid = ticket_id.strip().upper()
    ticket = TICKETS_DB.get(tid)
    if not ticket:
        return {"status_code": 404, "error": f"Ticket '{ticket_id}' not found."}

    new_comment = {
        "time": datetime.utcnow().isoformat() + "Z",
        "author": "Employee / Agent",
        "text": comment.strip(),
    }
    ticket["comments"].append(new_comment)
    return {
        "status_code": 200,
        "ticket_id": tid,
        "comment_added": True,
        "total_comments": len(ticket["comments"]),
        "origin": config.ORIGIN_HEADER_VALUE,
    }


def update_ticket_status(ticket_id: str, state: int, close_notes: Optional[str] = None) -> Dict[str, Any]:
    """Update incident lifecycle state with transition state-machine checks.
    Satisfies BRD: FR-4.2, FR-4.3.
    """
    tid = ticket_id.strip().upper()
    ticket = TICKETS_DB.get(tid)
    if not ticket:
        return {"status_code": 404, "error": f"Ticket '{ticket_id}' not found."}

    current_state = ticket["state"]
    if state not in STATE_MAP:
        return {"status_code": 400, "error": f"Invalid state '{state}'. Valid states: {STATE_MAP}."}

    # State Machine Transition Guardrails:
    # State 1 (New) cannot jump directly to 7 (Closed) without being Resolved (6) first.
    if current_state == 1 and state == 7:
        return {
            "status_code": 400,
            "error": "State machine transition violation: Ticket cannot transition directly from 'New' (1) to 'Closed' (7). Must transition to 'Resolved' (6) first.",
        }

    ticket["state"] = state
    ticket["state_label"] = STATE_MAP[state]
    if close_notes:
        ticket["close_notes"] = close_notes.strip()

    return {
        "status_code": 200,
        "ticket_id": tid,
        "previous_state": current_state,
        "current_state": state,
        "current_state_label": ticket["state_label"],
        "close_notes": ticket["close_notes"],
        "origin": config.ORIGIN_HEADER_VALUE,
    }
