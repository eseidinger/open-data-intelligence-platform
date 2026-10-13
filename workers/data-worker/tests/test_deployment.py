import importlib.util
import json
from pathlib import Path
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
        declaration=renderer.render("a"*40,"web.odip.test","identity.test","APP_ODIP_WORKER")
        Draft202012Validator({**snapshot,"$ref":"#/$defs/ApplicationEnvelopeV1Alpha2"}).validate(declaration)
        policy=json.loads((ROOT/"infrastructure/integration/odip-access-policy.json").read_text())
        Draft202012Validator({**snapshot,"$ref":"#/$defs/PolicyCreate"}).validate(policy)
        self.assertEqual([c["name"] for c in declaration["spec"]["components"] if c.get("exposure")=="public"],["web"])
        self.assertEqual(policy["component"],"web")
        self.assertTrue(all(":latest" not in c["runtime"]["image"] for c in declaration["spec"]["components"]))
        self.assertEqual(declaration["spec"]["configuration"]["values"]["ODIP_API_URL"],"https://web.odip.test")
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
    def test_renderer_rejects_floating_tags_placeholder_hosts_and_missing_bindings(self):
        for tag,host,prefix in [("latest","web.odip.test","APP_BINDING"),("a"*40,"example.invalid","APP_BINDING"),("a"*40,"web.odip.test","bad-prefix")]:
            with self.assertRaises(ValueError): renderer.render(tag,host,"identity.test",prefix)

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
