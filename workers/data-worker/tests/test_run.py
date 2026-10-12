import sys
import unittest
from unittest.mock import Mock, patch
import requests
from odip_worker.run import main, platform_principal_headers

class ClaimNextTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict("os.environ", {"ODIP_IDENTITY_MODE": "development"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_exits_successfully_when_no_queued_run_exists(self):
        response = Mock(status_code=204)
        with patch.object(sys, "argv", ["odip-ingest", "--claim-next"]), patch("odip_worker.run.claim_and_validate", return_value=False), patch("odip_worker.auth.requests.post", return_value=response) as post:
            main()
        post.assert_called_once_with("http://localhost:8080/api/pipeline-runs/claim-next", headers=platform_principal_headers(), timeout=(10,60), allow_redirects=False)

    def test_retries_a_transient_api_connection_failure(self):
        response = Mock(status_code=204)
        with patch.object(sys, "argv", ["odip-ingest", "--claim-next"]), patch("odip_worker.run.claim_and_validate", return_value=False), patch("odip_worker.auth.requests.post", side_effect=[requests.ConnectionError("API starting"), response]) as post, patch("odip_worker.run.time.sleep") as sleep:
            main()
        self.assertEqual(post.call_count,2)
        sleep.assert_called_once_with(5)

    def test_uses_a_configured_service_principal(self):
        with patch.dict("os.environ", {"ODIP_IDENTITY_MODE":"development", "ODIP_API_PRINCIPAL_ID":"prn_worker", "ODIP_API_PRINCIPAL_ISSUER":"https://identity.test", "ODIP_API_PRINCIPAL_SUBJECT":"worker-subject", "ODIP_API_PRINCIPAL_GROUP_IDS":"grp_users"}, clear=True):
            headers = platform_principal_headers()
            self.assertEqual(headers["X-Platform-Principal-Id"],"prn_worker")
            self.assertEqual(headers["X-Platform-Principal-Kind"],"service")
            self.assertEqual(headers["X-Platform-Principal-Client-Id"],"development-worker")
