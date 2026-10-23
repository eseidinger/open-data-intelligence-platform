import unittest
from unittest.mock import Mock, patch

import odip_worker.auth as auth
from odip_worker.auth import api_url, call, headers
from odip_worker.retrieval import destination, download


class BoundaryTests(unittest.TestCase):
    def test_private_and_mixed_dns_are_rejected(self):
        for addresses in [
            ["127.0.0.1"],
            ["169.254.169.254"],
            ["8.8.8.8", "10.0.0.1"],
            ["::1"],
        ]:
            with (
                patch.dict("os.environ", {"ODIP_SOURCE_HOSTS": "source.test"}),
                patch(
                    "socket.getaddrinfo",
                    return_value=[(2, 1, 6, "", (a, 443)) for a in addresses],
                ),
            ):
                with self.assertRaises(ValueError):
                    destination("https://source.test/file")

    def test_unapproved_protocol_and_credentials_fail(self):
        for url in [
            "http://source.test/a",
            "https://user:pass@source.test/a",
            "https://other.test/a",
            "https://source.test:8443/a",
        ]:
            with patch.dict("os.environ", {"ODIP_SOURCE_HOSTS": "source.test"}):
                with self.assertRaises(ValueError):
                    destination(url)

    def test_oversized_stream_closes_connection(self):
        response = Mock(status=200, headers={"Content-Type": "application/json"})
        response.stream.return_value = [b"x" * (10 * 1024 * 1024), b"x"]
        pool = Mock()
        pool.urlopen.return_value = response
        with (
            patch(
                "odip_worker.retrieval.destination",
                return_value=(
                    __import__("urllib.parse", fromlist=["urlsplit"]).urlsplit(
                        "https://source.test/file"
                    ),
                    "8.8.8.8",
                ),
            ),
            patch("urllib3.HTTPSConnectionPool", return_value=pool),
        ):
            with self.assertRaises(ValueError):
                download("https://source.test/file")
        response.close.assert_called_once()
        pool.close.assert_called_once()

    def test_platform_mode_requires_https_and_managed_credentials(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                api_url("http://localhost:8080")
            auth._cached_token = None
            with self.assertRaises(KeyError):
                headers()

    def test_tokens_are_cached_and_never_sent_as_identity_headers(self):
        auth._cached_token = None
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "example-token",
            "expires_in": 300,
            "token_type": "Bearer",
        }
        with (
            patch.dict(
                "os.environ",
                {
                    "ODIP_WORKER_BINDING_PREFIX": "BINDING",
                    "BINDING_TOKEN_URL": "https://identity.test/token",
                    "BINDING_CLIENT_ID": "client",
                    "BINDING_CLIENT_SECRET": "secret",
                },
                clear=True,
            ),
            patch("requests.post", return_value=response) as post,
        ):
            self.assertEqual(headers(), {"Authorization": "Bearer example-token"})
            self.assertEqual(headers(), {"Authorization": "Bearer example-token"})
            self.assertEqual(post.call_count, 1)
        auth._cached_token = None

    def test_api_redirect_never_forwards_credentials(self):
        with (
            patch.dict("os.environ", {"ODIP_IDENTITY_MODE": "development"}),
            patch("requests.get", return_value=Mock(status_code=302)) as get,
        ):
            with self.assertRaises(RuntimeError):
                call("get", "https://odip.test/api")
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
