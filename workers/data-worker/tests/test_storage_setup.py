import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("setup_storage", ROOT / "scripts/setup-storage.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
RESOURCE_ID = "94983c92-41c2-439c-887b-3a6b59509633"
BINDING_ID = "59b4c8c3-6311-4ba8-b32c-218377cf25ec"
DESIRED = json.loads(storage.RESOURCE.read_text())


class FakeCLI:
    def __init__(self):
        self.resource = None
        self.binding = None
        self.writes = []
        self.manage = True

    def invoke(self, arguments, body=None):
        if body is not None:
            self.writes.append((arguments, body))
        command = arguments[:2]
        if command == ["stores", "context"]:
            return {"project": "odip", "manage": self.manage,
                    "providers": [{"id": "postgresql", "enabled": True}]}
        if command == ["stores", "list"]:
            return {"resources": [copy.deepcopy(self.resource)] if self.resource else []}
        if command == ["stores", "create"]:
            self.resource = {**body, "resource_id": RESOURCE_ID, "owner_project": "odip",
                             "state": "active", "observed_state": "pending"}
            return copy.deepcopy(self.resource)
        if command == ["stores", "get"]:
            self.resource["observed_state"] = "active"
            return copy.deepcopy(self.resource)
        if arguments[:3] == ["stores", "bindings", "list"]:
            if self.binding:
                self.binding["observed_state"] = "active"
            return {"bindings": [copy.deepcopy(self.binding)] if self.binding else []}
        if arguments[:3] == ["stores", "bindings", "request"]:
            self.binding = {**body, "grant_id": BINDING_ID, "consumer_project": "odip",
                            "kind": "binding", "state": "active", "observed_state": "pending"}
            return copy.deepcopy(self.binding)
        raise AssertionError(arguments)


class StorageTests(unittest.TestCase):
    def test_preview_creates_nothing(self):
        cli = FakeCLI()
        result = storage.setup(cli, "odip", DESIRED)
        self.assertEqual(result["resource_action"], "create")
        self.assertEqual(result["binding_action"], "request")
        self.assertEqual(cli.writes, [])

    def test_apply_creates_resource_then_web_binding_and_rerun_reuses_both(self):
        cli = FakeCLI()
        result = storage.setup(cli, "odip", DESIRED, apply=True)
        self.assertEqual(result["ODIP_DATABASE_BINDING_ID"], BINDING_ID)
        self.assertEqual(result["observed_state"], "active")
        self.assertEqual([command[:3] for command, _ in cli.writes],
                         [["stores", "create", "--project"], ["stores", "bindings", "request"]])
        self.assertEqual(cli.writes[1][1], {"resource_id": RESOURCE_ID, "component": "web", "mode": "read-write"})
        cli.writes.clear()
        self.assertEqual(storage.setup(cli, "odip", DESIRED, apply=True), result)
        self.assertEqual(cli.writes, [])

    def test_resource_survives_failed_binding_request_and_rerun_reuses_it(self):
        cli = FakeCLI()
        invoke = cli.invoke

        def interrupted(arguments, body=None):
            if arguments[:3] == ["stores", "bindings", "request"]:
                raise storage.StorageError("CLI timed out")
            return invoke(arguments, body)

        with patch.object(cli, "invoke", side_effect=interrupted):
            with self.assertRaises(storage.StorageError):
                storage.setup(cli, "odip", DESIRED, apply=True)
        self.assertIsNotNone(cli.resource)
        cli.writes.clear()
        storage.setup(cli, "odip", DESIRED, apply=True)
        self.assertEqual(len(cli.writes), 1)
        self.assertEqual(cli.writes[0][0][:3], ["stores", "bindings", "request"])

    def test_conflicting_resource_is_never_modified(self):
        for field, value in (("provider", "s3"), ("quota_bytes", 2), ("state", "retired"), ("extensions", ["vector"])):
            cli = FakeCLI()
            storage.setup(cli, "odip", DESIRED, apply=True)
            cli.writes.clear()
            cli.resource[field] = value
            with self.subTest(field=field), self.assertRaises(storage.StorageError):
                storage.setup(cli, "odip", DESIRED, apply=True)
            self.assertEqual(cli.writes, [])

    def test_conflicting_binding_is_never_changed(self):
        for field, value in (("mode", "read-only"), ("state", "pending"), ("resource_id", BINDING_ID)):
            cli = FakeCLI()
            storage.setup(cli, "odip", DESIRED, apply=True)
            cli.writes.clear()
            cli.binding[field] = value
            with self.subTest(field=field), self.assertRaises(storage.StorageError):
                storage.setup(cli, "odip", DESIRED, apply=True)
            self.assertEqual(cli.writes, [])

    def test_requires_admin_before_writes(self):
        cli = FakeCLI()
        cli.manage = False
        with self.assertRaisesRegex(storage.StorageError, "administrator"):
            storage.setup(cli, "odip", DESIRED, apply=True)
        self.assertEqual(cli.writes, [])

    def test_wait_reports_failure_and_timeout_without_writes(self):
        with self.assertRaisesRegex(storage.StorageError, "failure"):
            storage.wait_active(lambda: {"error_code": "ProviderUnavailable"}, lambda row: None, 1)
        with self.assertRaisesRegex(storage.StorageError, "Timed out"):
            storage.wait_active(lambda: {"observed_state": "pending"}, lambda row: None,
                                1, clock=iter([0, 2]).__next__)

    def test_cli_uses_json_stdin_and_does_not_echo_errors(self):
        cli = storage.PlatformCLI("odip-lab")
        with patch.object(storage.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, '{"resource_id":"id"}', "")) as run:
            cli.invoke(["stores", "create", "--project", "odip", "--file", "-"], DESIRED)
        self.assertEqual(json.loads(run.call_args.kwargs["input"]), DESIRED)
        self.assertIn("odip-lab", run.call_args.args[0])
        with patch.object(storage.subprocess, "run", return_value=subprocess.CompletedProcess([], 3, "", "sensitive-value")):
            with self.assertRaises(storage.StorageError) as error:
                cli.invoke(["stores", "list", "--project", "odip"])
        self.assertNotIn("sensitive-value", str(error.exception))
        self.assertIn("devplat --profile odip-lab auth login", str(error.exception))
        self.assertIn("PLATFORM_ACCESS_TOKEN", str(error.exception))

    def test_invalid_project_prevents_cli_call(self):
        cli = FakeCLI()
        with self.assertRaises(storage.StorageError):
            storage.setup(cli, "--bad", DESIRED, apply=True)
        self.assertEqual(cli.writes, [])

    def test_apply_can_save_binding_in_existing_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "infrastructure/deployments/application.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            original = json.loads((ROOT / "infrastructure/deployments/application.json").read_text())
            path.write_text(json.dumps(original))
            with patch.object(storage.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "0.3.0\n", "")), \
                    patch.object(storage, "setup", return_value={"binding_id": BINDING_ID}), \
                    patch("builtins.print"):
                self.assertEqual(storage.main(["--apply", "--update-descriptor", str(path)]), 0)
            expected = copy.deepcopy(original)
            expected["spec"]["components"][0]["bindings"] = [{"bindingId": BINDING_ID, "envPrefix": ""}]
            self.assertEqual(json.loads(path.read_text()), expected)

    def test_descriptor_update_rejects_wrong_project_before_provisioning(self):
        with patch.object(storage, "setup") as provision, patch("builtins.print"):
            self.assertEqual(storage.main(["--apply", "--project", "odip-test", "--update-descriptor", str(ROOT / "infrastructure/deployments/application.json")]), 1)
        provision.assert_not_called()
