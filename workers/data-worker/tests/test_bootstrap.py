import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load("bootstrap-deployment")
worker = load("configure-worker-access")
DB = "94983c92-41c2-439c-887b-3a6b59509633"
GROUP = "grp_" + "a" * 32
SERVICE = "svc_" + "b" * 32


class FakeCLI:
    def __init__(self, project):
        self.project = project
        self.calls = []
        self.service = None
        self.current_components = []
        self.policy_state = "active"
        self.manage = True
        self.prefix = {"odip-test": "ACCESS_TEST", "odip": "ACCESS_PROD", "odip-test-local": "ACCESS_LOCAL"}[project]

    def invoke(self, args, body=None, **kwargs):
        self.calls.append((args, copy.deepcopy(body)))
        if "--project" in args:
            assert args[args.index("--project") + 1] == self.project
        if args[:2] == ["projects", "list"]:
            return [{"name": self.project, "status": "applied", "spec": {"components": self.current_components}}]
        if args[:2] == ["deploy", "apply"]:
            return {"state": "succeeded"}
        if args[:2] == ["access", "context"]:
            return {"project": self.project, "application": self.project, "component": "web",
                    "eligible": True, "permissions": {"manage": self.manage, "consume": True}}
        if args[:3] == ["access", "policy", "get"]:
            return {"state": self.policy_state}
        if args[:3] == ["access", "groups", "list"]:
            return {"items": [{"name": "ingestion-workers", "id": GROUP, "state": "active"}]}
        if args[:3] == ["access", "services", "list"]:
            return {"items": [copy.deepcopy(self.service)] if self.service else []}
        if args[:3] == ["access", "services", "request"]:
            assert "--project-wide-credential" in args
            self.service = {"id": SERVICE, "name": self.project + "-worker", "project": self.project,
                            "state": "pending", "etag": '"1"', "spec": copy.deepcopy(body)}
            return copy.deepcopy(self.service)
        if args[:3] == ["access", "services", "approve"]:
            assert args[3] == SERVICE
            assert args[args.index("--group") + 1] == GROUP
            assert args[args.index("--if-match") + 1] == '"1"'
            self.service["state"] = "active"
            self.service["spec"].update(groups=[GROUP], secretPrefix=self.prefix, principalId="prn_worker")
            return copy.deepcopy(self.service)
        raise AssertionError(args)


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        destination = self.root / "infrastructure/deployments"
        destination.mkdir(parents=True)
        for filename in tuple(bootstrap.DESCRIPTORS.values()):
            declaration = json.loads((ROOT / "infrastructure/deployments" / filename).read_text())
            declaration["spec"]["components"][0]["bindings"] = [{"bindingId": DB, "envPrefix": ""}]
            declaration["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"] = "SETUP_REQUIRED"
            (destination / filename).write_text(json.dumps(declaration))
        for module in (bootstrap, worker.bootstrap):
            guard = patch.object(module, "ROOT", self.root)
            guard.start()
            self.addCleanup(guard.stop)

    def test_bootstrap_both_environments_preserves_saved_descriptors(self):
        schema = json.loads((ROOT / "infrastructure/integration/application.schema.json").read_text())
        for project, version in (("odip-test", None), ("odip-test-local", None), ("odip", "v0.4.1")):
            path = bootstrap.descriptor_path(project)
            before = path.read_bytes()
            declaration = bootstrap.declaration(project, version)
            Draft202012Validator(schema).validate(declaration)
            self.assertEqual([c["name"] for c in declaration["spec"]["components"]], ["web"])
            self.assertNotIn("ODIP_WORKER_BINDING_PREFIX", declaration["spec"]["configuration"]["values"])
            self.assertEqual(declaration["spec"]["components"][0]["bindings"][0]["bindingId"], DB)
            self.assertTrue(declaration["spec"]["components"][0]["runtime"]["image"].endswith(":latest" if version is None else ":0.4.1"))
            self.assertEqual(path.read_bytes(), before)
            cli = FakeCLI(project)
            bootstrap.deploy(cli, project, declaration, 120)
            self.assertEqual(cli.calls[-1][0][:2], ["deploy", "apply"])
            self.assertIn("--wait", cli.calls[-1][0])

    def test_bootstrap_rejects_missing_binding_or_inappropriate_version(self):
        with self.assertRaises(bootstrap.storage.StorageError):
            bootstrap.declaration("odip")
        with self.assertRaises(bootstrap.storage.StorageError):
            bootstrap.declaration("odip-test", "v0.4.1")
        path = bootstrap.descriptor_path("odip-test")
        declaration = json.loads(path.read_text())
        declaration["spec"]["components"][0]["bindings"] = []
        path.write_text(json.dumps(declaration))
        with self.assertRaises(bootstrap.storage.StorageError):
            bootstrap.declaration("odip-test")

    def test_bootstrap_cannot_remove_existing_worker(self):
        cli = FakeCLI("odip-test")
        cli.current_components = [{"name": "web"}, {"name": "ingestion-worker"}]
        with self.assertRaisesRegex(bootstrap.storage.StorageError, "would remove"):
            bootstrap.deploy(cli, "odip-test", bootstrap.declaration("odip-test"), 120)
        self.assertFalse(any(body is not None for _, body in cli.calls))

    def test_worker_preview_is_read_only(self):
        cli = FakeCLI("odip-test")
        path = worker.bootstrap.descriptor_path("odip-test")
        before = path.read_bytes()
        result = worker.configure(cli, "odip-test")
        self.assertEqual(result["action"], "request-and-approve")
        self.assertIsNone(cli.service)
        self.assertEqual(path.read_bytes(), before)

    def test_worker_setup_and_repeat_run_for_both_projects(self):
        for project in bootstrap.DESCRIPTORS:
            cli = FakeCLI(project)
            path = worker.bootstrap.descriptor_path(project)
            expected = json.loads(path.read_text())
            result = worker.configure(cli, project, apply=True)
            self.assertEqual(result["worker_binding_prefix"], cli.prefix)
            self.assertEqual(result["principal_id"], "prn_worker")
            expected["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"] = cli.prefix
            self.assertEqual(json.loads(path.read_text()), expected)
            self.assertEqual(sum(body is not None for _, body in cli.calls), 1)
            self.assertEqual(sum(args[:3] == ["access", "services", "approve"] for args, _ in cli.calls), 1)
            cli.calls.clear()
            worker.configure(cli, project, apply=True)
            self.assertFalse(any(args[:3] in (["access", "services", "request"], ["access", "services", "approve"]) for args, _ in cli.calls))

    def test_failed_request_is_not_retried_and_next_run_reuses_accepted_request(self):
        cli = FakeCLI("odip-test")
        original = cli.invoke

        def interrupted(args, body=None, **kwargs):
            result = original(args, body, **kwargs)
            if args[:3] == ["access", "services", "request"]:
                raise worker.storage.StorageError("Connection lost after submission")
            return result

        path = worker.bootstrap.descriptor_path("odip-test")
        before = path.read_bytes()
        with patch.object(cli, "invoke", side_effect=interrupted):
            with self.assertRaises(worker.storage.StorageError):
                worker.configure(cli, "odip-test", apply=True)
        self.assertEqual(sum(args[:3] == ["access", "services", "request"] for args, _ in cli.calls), 1)
        self.assertEqual(path.read_bytes(), before)
        cli.calls.clear()
        worker.configure(cli, "odip-test", apply=True)
        self.assertFalse(any(args[:3] == ["access", "services", "request"] for args, _ in cli.calls))

    def test_worker_setup_requires_active_policy_and_administrator(self):
        for change in ("policy", "permissions"):
            cli = FakeCLI("odip-test")
            if change == "policy":
                cli.policy_state = "provisioning"
            else:
                cli.manage = False
            with self.subTest(change=change), self.assertRaises(worker.storage.StorageError):
                worker.configure(cli, "odip-test", apply=True)
            self.assertIsNone(cli.service)

    def test_existing_conflicting_access_or_prefix_is_not_saved(self):
        for change in ("provider", "groups", "state", "prefix"):
            cli = FakeCLI("odip-test")
            worker.configure(cli, "odip-test", apply=True)
            if change == "provider":
                cli.service["spec"]["providerProject"] = "odip"
            elif change == "groups":
                cli.service["spec"]["groups"].append("grp_other")
            elif change == "state":
                cli.service["state"] = "revoked"
            else:
                cli.service["spec"]["secretPrefix"] = "invalid-prefix"
            path = worker.bootstrap.descriptor_path("odip-test")
            before = path.read_bytes()
            cli.calls.clear()
            with self.subTest(change=change), self.assertRaises(worker.storage.StorageError):
                worker.configure(cli, "odip-test", apply=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(any(args[:3] in (["access", "services", "request"], ["access", "services", "approve"]) for args, _ in cli.calls))

    def test_provisioning_timeout_does_not_save_prefix_or_approve_again(self):
        cli = FakeCLI("odip-test")
        worker.configure(cli, "odip-test", apply=True)
        cli.service["state"] = "provisioning"
        cli.calls.clear()
        with self.assertRaisesRegex(worker.storage.StorageError, "did not activate"):
            worker.configure(cli, "odip-test", apply=True, timeout=1, clock=iter([0, 2]).__next__, sleep=lambda _: None)
        self.assertFalse(any(args[:3] == ["access", "services", "approve"] for args, _ in cli.calls))
