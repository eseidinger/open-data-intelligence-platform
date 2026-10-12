import sys
import unittest
from unittest.mock import Mock, patch

import requests

from odip_worker.run import main, platform_principal_headers


class ClaimNextTests(unittest.TestCase):
    def test_exits_successfully_when_no_queued_run_exists(self) -> None:
        response = Mock(status_code=204)
        with patch.object(sys, "argv", ["odip-ingest", "--claim-next"]), patch("odip_worker.run.requests.post", return_value=response) as post:
            main()

        post.assert_called_once_with(
            "http://localhost:8080/api/pipeline-runs/claim-next",
            headers=platform_principal_headers(),
            timeout=15,
        )

    def test_retries_a_transient_api_connection_failure(self) -> None:
        unavailable = requests.ConnectionError("API is starting")
        response = Mock(status_code=204)
        with patch.object(sys, "argv", ["odip-ingest", "--claim-next"]), patch("odip_worker.run.requests.post", side_effect=[unavailable, response]) as post, patch("odip_worker.run.time.sleep") as sleep:
            main()

        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_uses_a_configured_service_principal(self) -> None:
        with patch.dict("os.environ", {
            "ODIP_API_PRINCIPAL_ID": "prn_worker",
            "ODIP_API_PRINCIPAL_KIND": "service",
            "ODIP_API_PRINCIPAL_ISSUER": "https://identity.test",
            "ODIP_API_PRINCIPAL_SUBJECT": "worker-subject",
            "ODIP_API_PRINCIPAL_GROUP_IDS": "grp_users",
        }, clear=True):
            self.assertEqual(platform_principal_headers(), {
                "X-Platform-Principal-Id": "prn_worker",
                "X-Platform-Principal-Kind": "service",
                "X-Platform-Principal-Issuer": "https://identity.test",
                "X-Platform-Principal-Subject": "worker-subject",
                "X-Platform-Principal-Group-Ids": "grp_users",
            })
