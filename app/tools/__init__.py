"""Tool suite for Altostrat HR Agent."""
from .policy_tool import search_policy_docs, list_concepts, read_concept
from .hrms_tool import (
    get_employee_profile,
    get_leave_balances,
    submit_leave_request,
    update_contact_info,
    cancel_leave_request,
)
from .itms_tool import (
    get_incident_ticket,
    create_incident_ticket,
    add_ticket_comment,
    update_ticket_status,
)
from .workflow_tool import execute_medical_leave_workflow
from .mcp_client import MCPClient, default_mcp_client

__all__ = [
    "search_policy_docs",
    "list_concepts",
    "read_concept",
    "get_employee_profile",
    "get_leave_balances",
    "submit_leave_request",
    "update_contact_info",
    "cancel_leave_request",
    "get_incident_ticket",
    "create_incident_ticket",
    "add_ticket_comment",
    "update_ticket_status",
    "execute_medical_leave_workflow",
    "MCPClient",
    "default_mcp_client",
]
