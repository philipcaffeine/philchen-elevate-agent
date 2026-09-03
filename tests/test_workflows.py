"""Tests for Cross-System Orchestration Flow & Compensation (UC-2.2)."""
import unittest
from app.tools import execute_medical_leave_workflow, get_leave_balances


class TestWorkflows(unittest.TestCase):

    def test_cross_system_medical_leave_success(self):
        # Initial balance check
        init_bal = get_leave_balances("EMP1024")
        sick_start = init_bal["sick_remaining"]

        # Execute 3 days medical leave
        result = execute_medical_leave_workflow(
            employee_id="EMP1024",
            start_date="2026-09-14",
            end_date="2026-09-16",
            days=3.0,
            simulate_ticket_failure=False,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["leave_request_id"].startswith("LOA-"))
        self.assertTrue(result["incident_ticket_id"].startswith("INC-"))

        # Verify balance deducted
        post_bal = get_leave_balances("EMP1024")
        self.assertEqual(post_bal["sick_remaining"], sick_start - 3.0)

    def test_cross_system_medical_leave_compensation(self):
        # Initial balance check
        init_bal = get_leave_balances("EMP1024")
        sick_before = init_bal["sick_remaining"]

        # Execute medical leave with simulated ITMS ticket failure
        result = execute_medical_leave_workflow(
            employee_id="EMP1024",
            start_date="2026-09-21",
            end_date="2026-09-23",
            days=2.0,
            simulate_ticket_failure=True,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["step"], "itms_ticket_creation")
        self.assertTrue(result["compensation_executed"])
        self.assertEqual(result["compensation_status"], "CANCELLED")
        self.assertEqual(result["refunded_days"], 2.0)

        # Verify balance was restored by compensation
        post_bal = get_leave_balances("EMP1024")
        self.assertEqual(post_bal["sick_remaining"], sick_before)


if __name__ == "__main__":
    unittest.main()
