"""Tests for Enterprise Tools (PolicyTool, HRMS, ITMS)."""
import unittest
from app.tools import (
    search_policy_docs,
    read_concept,
    list_concepts,
    get_employee_profile,
    get_leave_balances,
    submit_leave_request,
    update_contact_info,
    get_incident_ticket,
    create_incident_ticket,
    add_ticket_comment,
    update_ticket_status,
)
from app.tools.hrms_tool import EMPLOYEE_DB


class TestTools(unittest.TestCase):

    def setUp(self):
        # Reset balances before each test
        EMPLOYEE_DB["EMP1024"]["balances"] = {
            "vacation": {"accrued": 18.0, "used": 4.0, "remaining": 14.0},
            "sick": {"accrued": 14.0, "used": 2.0, "remaining": 12.0},
        }

    def test_policy_search_and_grounding(self):
        # Valid query
        res = search_policy_docs("sick leave hospitalization")
        self.assertTrue(res["found"])
        self.assertIn("Sick", res["title"])
        self.assertGreaterEqual(res.get("confidence", 0), 0.65)

        # Completely ungrounded query -> triggers refusal gate
        ungrounded = search_policy_docs("how to repair a nuclear submarine reactor")
        self.assertFalse(ungrounded["found"])
        self.assertIn("there is no policy on file", ungrounded["message"])

    def test_hrms_profile_and_balances(self):
        profile = get_employee_profile("EMP1024")
        self.assertEqual(profile["status_code"], 200)
        self.assertEqual(profile["name"], "Alex Tan")

        balances = get_leave_balances("EMP1024")
        self.assertEqual(balances["status_code"], 200)
        self.assertEqual(balances["vacation_remaining"], 14.0)
        self.assertEqual(balances["sick_remaining"], 12.0)

    def test_hrms_leave_request_guardrails(self):
        # Balance overdraft attempt: requesting 50 days when only 14 available
        overdraft = submit_leave_request("EMP1024", "Vacation", "2026-09-10", "2026-09-20", 50.0)
        self.assertEqual(overdraft["status_code"], 422)
        self.assertIn("Insufficient balance", overdraft["error"])

        # Temporal violation: start_date > end_date
        temporal_err = submit_leave_request("EMP1024", "Vacation", "2026-09-20", "2026-09-10", 2.0)
        self.assertEqual(temporal_err["status_code"], 400)
        self.assertIn("Temporal violation", temporal_err["error"])

        # Valid submission: 2 days vacation
        valid = submit_leave_request("EMP1024", "Vacation", "2026-09-10", "2026-09-12", 2.0)
        self.assertEqual(valid["status_code"], 201)
        self.assertTrue(valid["request_id"].startswith("LOA-"))
        self.assertEqual(valid["remaining_balance"], 12.0)

    def test_itms_incident_lifecycle_guardrails(self):
        # Create valid ticket
        ticket = create_incident_ticket("EMP1024", "HRSD", "Request email delegation setup", "3 - Moderate")
        self.assertEqual(ticket["status_code"], 201)
        tid = ticket["ticket_id"]

        # Duplicate mitigation check
        dup = create_incident_ticket("EMP1024", "HRSD", "Request email delegation setup", "3 - Moderate")
        self.assertEqual(dup["status_code"], 409)
        self.assertIn("Duplicate ticket mitigation", dup["error"])

        # Invalid state transition: New (1) -> Closed (7) directly
        invalid_trans = update_ticket_status(tid, 7)
        self.assertEqual(invalid_trans["status_code"], 400)
        self.assertIn("State machine transition violation", invalid_trans["error"])

        # Valid state transition: New (1) -> In Progress (2) -> Resolved (6)
        t_prog = update_ticket_status(tid, 2)
        self.assertEqual(t_prog["status_code"], 200)
        self.assertEqual(t_prog["current_state"], 2)

        t_res = update_ticket_status(tid, 6, close_notes="Completed setup")
        self.assertEqual(t_res["status_code"], 200)
        self.assertEqual(t_res["current_state"], 6)


if __name__ == "__main__":
    unittest.main()
