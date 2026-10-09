import frappe
import unittest
from unittest.mock import patch, MagicMock
from hrms.api.haven import get_weekly_metrics
import datetime
import hashlib
import json

class TestHavenDerivedMetrics(unittest.TestCase):
    @patch("hrms.api.haven.requests.post")
    @patch("hrms.api.haven.frappe.get_all")
    @patch("hrms.api.haven.frappe.db.get_value")
    @patch("hrms.api.haven.frappe.get_doc")
    @patch("hrms.api.haven.frappe.db.count")
    def test_derived_metrics_logic(self, mock_count, mock_get_doc, mock_get_value, mock_get_all, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "Success"
        
        def mock_get_all_side_effect(doctype, **kwargs):
            if doctype == "Employee":
                return [frappe._dict({"name": "HRMS-EMP-TEST", "department": "Eng", "designation": "Dev", "date_of_joining": "2020-01-01", "employment_type": "Full", "reports_to": None})]
            if doctype == "Attendance":
                return [
                    frappe._dict({"attendance_date": "2026-10-01", "status": "Present", "working_hours": 8, "late_entry": 0, "early_exit": 0, "out_time": "18:00:00"}), # Thursday
                    frappe._dict({"attendance_date": "2026-10-02", "status": "Present", "working_hours": 8, "late_entry": 0, "early_exit": 0, "out_time": None}), # Friday, missing checkout
                    frappe._dict({"attendance_date": "2026-10-03", "status": "Present", "working_hours": 8, "late_entry": 0, "early_exit": 0, "out_time": "18:00:00"}), # Saturday (weekend)
                    frappe._dict({"attendance_date": "2026-10-05", "status": "Present", "working_hours": 8, "late_entry": 0, "early_exit": 0, "out_time": "18:00:00"}), # Monday (streak broken)
                    frappe._dict({"attendance_date": "2026-10-05", "status": "Present", "working_hours": 0, "late_entry": 0, "early_exit": 0, "out_time": "18:00:00"}) # Duplicate date prevention
                ]
            if doctype == "Timesheet":
                return [frappe._dict({"total_hours": 45})]
            if doctype == "Leave Application":
                return [
                    frappe._dict({"posting_date": "2026-10-01", "from_date": "2026-10-02"}), # Unplanned (1 day)
                    frappe._dict({"posting_date": "2026-10-01", "from_date": "2026-10-10"})  # Planned (9 days)
                ]
            if doctype == "Salary Slip":
                return [frappe._dict({"status": "Failed"}), frappe._dict({"status": "Submitted"})]
            if doctype == "Appraisal":
                return [frappe._dict({"total_score": 4.5})]
            return []

        mock_get_all.side_effect = mock_get_all_side_effect
        mock_get_value.return_value = "Standard Shift"
        mock_get_doc.return_value = frappe._dict({
            "start_time": "09:00:00",
            "end_time": "17:00:00"  # 8 hours scheduled
        })
        mock_count.return_value = 0
        
        # Setup configs
        import jwcrypto.jwk as jwk
        test_key = jwk.JWK.generate(kty='RSA', size=2048)
        public_pem = test_key.export_to_pem(private_key=False).decode('utf-8')
        
        frappe.conf.haven_public_key = public_pem
        frappe.conf.haven_service_token = "test-token"
        frappe.conf.haven_api_url = "http://test.url"
        
        # We need to capture the exact JWE payload being sent
        captured_payloads = []
        def capture_post(*args, **kwargs):
            captured_payloads.append(kwargs.get("json"))
            resp = MagicMock()
            resp.status_code = 200
            return resp
            
        mock_post.side_effect = capture_post

        # Run the function
        results = get_weekly_metrics()
        
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(len(captured_payloads), 1)
        
        # Decrypt JWE to verify payload
        from jwcrypto import jwe
        enc_compact = captured_payloads[0]["jwe"]
        jwetoken = jwe.JWE()
        jwetoken.deserialize(enc_compact, key=test_key)
        payload = json.loads(jwetoken.payload.decode('utf-8'))
        
        # Assertions
        # 1. Overtime: actual(45) - scheduled(8 * 5 = 40) = 5
        self.assertEqual(payload["overtime_hours"], 5.0)
        # 2. Missing checkout: 1
        self.assertEqual(payload["missing_checkout_count"], 1)
        # 3. Weekend workdays: 1 (Oct 3rd)
        self.assertEqual(payload["weekend_work_days"], 1)
        # 4. Consecutive workdays: Oct 1, 2, 3 = 3 days.
        self.assertEqual(payload["consecutive_work_days"], 3)
        # 5. Unplanned leaves: 1
        self.assertEqual(payload["unplanned_leave_count"], 1)
        # 6. Payroll issues: 1 (Failed)
        self.assertEqual(payload["payroll_issue_count"], 1)
        # 7. Data completeness: > 0.4
        self.assertTrue(payload["data_completeness"] > 0.4)
        
        # Unavailable metric returning None
        self.assertIsNone(payload["night_shift_count"])
        self.assertIsNone(payload["goal_completion_percent"])
        
        # Replay and transmission standard fields
        self.assertIn("request_id", payload)
        self.assertIn("timestamp", payload)
        self.assertIn("week_start_date", payload)
        self.assertIn("employee_hash", payload)
