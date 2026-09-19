"""Offline regression tests. No real credentials or school requests are used."""
import contextlib
import hashlib
import io
import logging
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import runner
import signin_core as core

logging.disable(logging.CRITICAL)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.user = core.User(student_Id=100000001, password="test-only-value")

    def test_sign_code_uses_current_milliseconds(self):
        now = datetime(2026, 9, 19, 21, 35, tzinfo=runner.BEIJING)
        expected_text = "Sat Sep 19 2026 21:35:00 GMT+0800 (中国标准时间)"
        expected = hashlib.md5(expected_text.encode()).hexdigest()
        with patch.object(core.time, "time", return_value=now.timestamp()):
            self.assertEqual(core.generate_data(self.user)["signCode"], expected)

    def test_non_object_response_is_not_a_valid_api_result(self):
        for body in ('[]', 'true', '"success"', 'null', '<html>error</html>'):
            self.assertIsNone(core._try_json_loads(body))

    def test_error_status_or_empty_token_cannot_authenticate(self):
        for response in ((500, {"refresh_token": "fake"}), (200, {"refresh_token": ""})):
            with patch.object(core, "http_request_json", return_value=response):
                self.assertFalse(core.sign_in_by_step(self.user, 0, debug=True)["success"])

    def test_missing_or_failed_location_does_not_advance(self):
        responses = [(500, {"code": 500}), (200, {"code": 200, "data": {}}),
                     (200, {"code": 200, "data": {"dormitoryRegisterVO": {
                         "locationLat": "nan", "locationLng": 118, "roomId": "test"}}})]
        for response in responses:
            with self.subTest(response=response), patch.object(core, "http_request_json", return_value=response):
                result = core.sign_in_by_step(self.user, 4, debug=True)
                self.assertFalse(result["success"])
                self.assertEqual(result["step"], 4)

    def test_location_failure_never_submits(self):
        requested = []

        def api(user, method, url, **kwargs):
            requested.append(url)
            if url == core.WEB_DICT["token_api"]:
                return 200, {"refresh_token": "fake"}
            if url == core.WEB_DICT["task_id_api"]:
                return 200, {"code": 200, "data": {"records": [{"taskId": 1}]}}
            if "getTaskByIdForApp" in url:
                return 500, {"code": 500, "msg": "test failure"}
            return 200, {"code": 200}

        with patch.object(core, "http_request_json", side_effect=api), patch.object(core.time, "sleep"):
            result = core.sign_in(self.user, debug=True)
        self.assertFalse(result["success"])
        self.assertEqual(result["step"], 4)
        self.assertNotIn(core.WEB_DICT["sign_in_api"], requested)

    def test_submission_requires_explicit_http_and_business_success(self):
        for response in ((200, {"code": -1, "msg": ""}), (500, {"code": 200}),
                         (200, {"code": 500, "msg": "failed"})):
            with patch.object(core, "http_request_json", return_value=response):
                self.assertFalse(core.sign_in_by_step(self.user, 5, debug=True)["success"])
        for response, outcome in (((200, {"code": 200}), "api_confirmed"),
                                  ((200, {"code": 500, "msg": "您今天已完成签到"}), "already_signed")):
            with patch.object(core, "http_request_json", return_value=response):
                self.assertEqual(core.sign_in_by_step(self.user, 5, debug=True)["outcome"], outcome)

    def test_reaching_final_step_alone_is_not_success(self):
        with patch.object(core, "sign_in_by_step", return_value={"success": False, "step": 6}), patch.object(core.time, "sleep"):
            self.assertFalse(core.sign_in(self.user, debug=True)["success"])

    def test_explicit_outcome_is_propagated(self):
        responses = [{"success": True, "step": n} for n in range(1, 6)]
        responses.append({"success": True, "step": 6, "outcome": "api_confirmed"})
        with patch.object(core, "sign_in_by_step", side_effect=responses), patch.object(core.time, "sleep"):
            self.assertEqual(core.sign_in(self.user, debug=True)["outcome"], "api_confirmed")


class RunnerTests(unittest.TestCase):
    def invoke(self, response=None, *, check=False, hour=21, minute=35, credentials=True):
        env = {"GITHUB_EVENT_NAME": "workflow_dispatch"}
        if credentials:
            env.update(AHUT_STUDENT_ID="100000001", AHUT_PASSWORD="SENTINEL-NOT-A-REAL-PASSWORD")
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.md"
            env["GITHUB_STEP_SUMMARY"] = str(summary)
            with patch.dict(os.environ, env, clear=True), patch.object(runner, "datetime") as clock, \
                    patch.object(core, "sign_in", return_value=response) as sign, contextlib.redirect_stdout(stream):
                clock.now.return_value = datetime(2026, 9, 19, hour, minute, tzinfo=runner.BEIJING)
                code = runner.run(check_only=check)
            return code, stream.getvalue(), summary.read_text(), sign.call_count

    def test_configuration_check_never_calls_school(self):
        code, log, summary, calls = self.invoke(check=True)
        self.assertEqual((code, calls), (0, 0))
        self.assertIn("configuration_only", summary)
        self.assertIn("没有提交签到", log)

    def test_missing_secrets_and_early_time_fail_without_requests(self):
        for options in ({"credentials": False}, {"hour": 21, "minute": 34}):
            code, _, _, calls = self.invoke(**options)
            self.assertEqual((code, calls), (2, 0))

    def test_ambiguous_success_is_rejected(self):
        for response in ({"success": True}, {"success": True, "outcome": "unknown"}, []):
            code, _, _, _ = self.invoke(response)
            self.assertEqual(code, 1)

    def test_summary_distinguishes_confirmation_and_already_signed(self):
        for outcome in ("api_confirmed", "already_signed"):
            code, _, summary, calls = self.invoke({"success": True, "outcome": outcome})
            self.assertEqual((code, calls), (0, 1))
            self.assertIn(outcome, summary)
            self.assertIn("尚未独立查询", summary)

    def test_failure_details_and_credentials_are_not_logged(self):
        response = {"success": False, "step": 4, "data": {"raw private body SENTINEL-NOT-A-REAL-PASSWORD"}}
        code, log, summary, _ = self.invoke(response)
        self.assertEqual(code, 1)
        self.assertIn("获取宿舍信息", summary)
        for secret in ("100000001", "SENTINEL-NOT-A-REAL-PASSWORD", "raw private body"):
            self.assertNotIn(secret, log + summary)


if __name__ == "__main__":
    unittest.main()
