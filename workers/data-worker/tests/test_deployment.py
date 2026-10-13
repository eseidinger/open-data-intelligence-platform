import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from jsonschema import Draft202012Validator
from odip_worker.contract import KIT

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("render_integration",ROOT/"scripts/render-integration.py")
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class DeploymentTests(unittest.TestCase):
    def test_rendered_declaration_and_policy_match_pinned_platform_schemas(self):
        snapshot=json.loads((KIT/"platform/upstream-inputs.schema.json").read_text())
        declaration=renderer.render("a"*40)
        Draft202012Validator({**snapshot,"$ref":"#/$defs/ApplicationEnvelopeV1Alpha2"}).validate(declaration)
        policy=json.loads((ROOT/"infrastructure/integration/odip-access-policy.json").read_text())
        Draft202012Validator({**snapshot,"$ref":"#/$defs/PolicyCreate"}).validate(policy)
        self.assertEqual([c["name"] for c in declaration["spec"]["components"] if c.get("exposure")=="public"],["web"])
        self.assertEqual(policy["component"],"web")
        self.assertTrue(all(":latest" not in c["runtime"]["image"] for c in declaration["spec"]["components"]))
        self.assertEqual(declaration["spec"]["configuration"]["values"]["ODIP_API_URL"],"https://web-odip.apps.eseidinger.de")
        self.assertEqual(declaration["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"],"ACCESS_BCC37E90DE10")
        self.assertTrue(all(c["runtime"]["image"].endswith(":" + "a"*40) for c in declaration["spec"]["components"]))
        worker = next(c for c in declaration["spec"]["components"] if c["name"] == "ingestion-worker")
        self.assertEqual({(rule["dns"], rule["port"]) for rule in worker["outbound"]}, {
            ("web-odip.apps.eseidinger.de", 443), ("identity.eseidinger.de", 443),
            ("jsonplaceholder.typicode.com", 443), ("ec.europa.eu", 443), ("re.jrc.ec.europa.eu", 443),
        })
        self.assertNotIn("ODIP_GROUP_IDS_USERS", declaration["spec"]["configuration"]["values"])
        self.assertNotIn("ODIP_GROUP_IDS_GUESTS", declaration["spec"]["configuration"]["values"])
        # Platform configuration refuses secret-like names even for harmless values.
        import re
        self.assertFalse(any(re.search(r"PASS|SECRET|TOKEN|CREDENTIAL|PRIVATE|API_?KEY|AUTH",key,re.I) for key in declaration["spec"]["configuration"]["values"]))
        def contains(match,path):
            return path==match["path"] if "path" in match else path==match["pathPrefix"] or path.startswith(match["pathPrefix"].rstrip("/")+"/")
        for index,left in enumerate(policy["routes"]):
            for right in policy["routes"][index+1:]:
                if set(left["match"]["methods"]) & set(right["match"]["methods"]):
                    lp=left["match"].get("path",left["match"].get("pathPrefix"))
                    rp=right["match"].get("path",right["match"].get("pathPrefix"))
                    self.assertFalse(contains(left["match"],rp) or contains(right["match"],lp))
    def test_renderer_rejects_floating_tags_and_missing_bindings(self):
        for tag, prefix in [("latest", "APP_BINDING"), ("a"*40, "bad-prefix"), ("a"*40, ""), ("a"*40, "RENDER_REQUIRED")]:
            with self.subTest(tag=tag, prefix=prefix), self.assertRaises(ValueError):
                renderer.render(tag, prefix)

    def test_renderer_preserves_installation_configuration_and_other_components(self):
        application = json.loads((ROOT / "application.json").read_text())
        values = application["spec"]["configuration"]["values"]
        values["ODIP_API_URL"] = "https://web.odip.test"
        values["ODIP_SOURCE_HOSTS"] = "source.odip.test"
        worker = application["spec"]["components"][1]
        worker["outbound"] = [{"dns": host, "port": 443} for host in ("web.odip.test", "identity.odip.test", "source.odip.test")]
        application["spec"]["components"].append({"name": "other", "runtime": {"image": "example/other:fixed"}})
        original = copy.deepcopy(application)
        declaration = renderer.render("a"*40, "APP_WORKER", application=application)
        expected = copy.deepcopy(original)
        expected["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"] = "APP_WORKER"
        expected["spec"]["components"][0]["runtime"]["image"] = "docker.io/eseidinger/odip-platform:" + "a"*40
        expected["spec"]["components"][1]["runtime"]["image"] = "docker.io/eseidinger/odip-data-worker:" + "a"*40
        self.assertEqual(declaration, expected)
        self.assertEqual(application, original)

    def test_renderer_rejects_invalid_descriptor_origins(self):
        for origin in ("", "https://example.invalid", "http://web.odip.test", "https://user:password@web.odip.test", "https://web.odip.test/api", "https://web.odip.test?query=value", "https://web.odip.test#fragment", "https://web.odip.test:8443", "https://bad..test"):
            application = json.loads((ROOT / "application.json").read_text())
            application["spec"]["configuration"]["values"]["ODIP_API_URL"] = origin
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                renderer.render("a"*40, "APP_WORKER", application=application)

    def test_renderer_requires_api_egress_and_rejects_placeholder_egress(self):
        for outbound in ([], [{"dns": "web-odip.apps.eseidinger.de", "port": 80}], [{"dns": "web-odip.apps.eseidinger.de", "port": 443}, {"dns": "identity.example.invalid", "port": 443}]):
            application = json.loads((ROOT / "application.json").read_text())
            application["spec"]["components"][1]["outbound"] = outbound
            with self.subTest(outbound=outbound), self.assertRaises(ValueError):
                renderer.render("a"*40, "APP_WORKER", application=application)

    def test_workflow_renderer_uses_descriptor_hosts_and_binding(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/render-integration.py"), "--image-tag", "a"*40], capture_output=True, text=True, check=True)
        declaration = json.loads(result.stdout)
        self.assertEqual(declaration, renderer.render("a"*40))
        self.assertEqual(declaration["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"], "ACCESS_BCC37E90DE10")
        workflow = (ROOT / ".github/workflows/platform-deploy.yml").read_text()
        for obsolete_input in ("ODIP_HOST", "IDENTITY_HOST", "--odip-host", "--identity-host", "vars.ODIP_WORKER_BINDING_PREFIX", "--worker-secret-prefix"):
            self.assertNotIn(obsolete_input, workflow)

    def test_renderer_rejects_missing_or_invalid_descriptor_bindings(self):
        for prefix in (None, "", "RENDER_REQUIRED", "bad-prefix", 123):
            application = json.loads((ROOT / "application.json").read_text())
            values = application["spec"]["configuration"]["values"]
            if prefix is None:
                values.pop("ODIP_WORKER_BINDING_PREFIX")
            else:
                values["ODIP_WORKER_BINDING_PREFIX"] = prefix
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                renderer.render("a"*40, application=application)

    def test_cli_accepts_installation_descriptor_file(self):
        application = json.loads((ROOT / "application.json").read_text())
        application["spec"]["configuration"]["values"]["ODIP_SOURCE_HOSTS"] = "jsonplaceholder.typicode.com"
        application["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"] = "ACCESS_OTHER_INSTALLATION"
        with tempfile.TemporaryDirectory() as directory:
            descriptor = Path(directory) / "application.json"
            descriptor.write_text(json.dumps(application))
            result = subprocess.run([sys.executable, str(ROOT / "scripts/render-integration.py"), "--file", str(descriptor), "--image-tag", "a"*40], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), renderer.render("a"*40, application=application))

    def test_cli_binding_override_takes_precedence(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/render-integration.py"), "--image-tag", "a"*40, "--worker-secret-prefix", "APP_WORKER"], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), renderer.render("a"*40, "APP_WORKER"))

    def test_cli_missing_binding_has_actionable_error_without_json_output(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/render-integration.py"), "--image-tag", "a"*40, "--worker-secret-prefix", ""], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Set ODIP_WORKER_BINDING_PREFIX", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_platform_policy_owns_role_checks_and_keeps_administration_separate(self):
        policy = json.loads((ROOT / "infrastructure/integration/odip-access-policy.json").read_text())
        def permitted(path, method, mode, group):
            for route in policy["routes"]:
                match = route["match"]
                matched = path == match["path"] if "path" in match else path == match["pathPrefix"] or path.startswith(match["pathPrefix"].rstrip("/") + "/")
                if matched and method in match["methods"]:
                    return route["authentication"]["mode"] == mode and group in route["authorization"]["anyOfGroups"]
            return False
        for path, method in [("/api/v1/dataset-grants/fixture", "PUT"), ("/api/v1/publication-retention", "PUT"), ("/api/data-sources", "POST"), ("/api/datasets", "POST"), ("/api/v1/operator-capabilities", "GET")]:
            self.assertTrue(permitted(path, method, "browser-session", "dataset-operators"))
            for group in ("dataset-readers", "ingestion-workers"):
                self.assertFalse(permitted(path, method, "browser-session", group))
                self.assertFalse(permitted(path, method, "bearer-token", group))
        self.assertTrue(permitted("/api/v1/datasets/fixture/versions/1.0.0", "GET", "bearer-token", "dataset-readers"))
        self.assertFalse(permitted("/api/v1/datasets", "POST", "bearer-token", "dataset-readers"))
        self.assertTrue(permitted("/api/pipeline-runs/claim-next", "POST", "bearer-token", "ingestion-workers"))
        self.assertFalse(permitted("/api/pipeline-runs/claim-next", "POST", "bearer-token", "dataset-readers"))
        for route in policy["routes"]:
            if route["authentication"]["mode"] == "browser-session":
                self.assertEqual(route["authorization"]["anyOfGroups"], ["dataset-operators"])
