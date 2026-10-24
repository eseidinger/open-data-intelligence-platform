import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from odip_worker.contract import KIT

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "render_release", ROOT / "scripts/render-release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class DeploymentTests(unittest.TestCase):
    def test_descriptors_match_platform_schema_and_target_separate_projects(self):
        schema = json.loads(
            (ROOT / "infrastructure/integration/application.schema.json").read_text()
        )
        for filename, project, tag in (
            ("infrastructure/deployments/application.json", "odip", "0.4.1"),
            ("infrastructure/deployments/application-test.json", "odip-test", "latest"),
        ):
            with self.subTest(filename=filename):
                declaration = json.loads((ROOT / filename).read_text())
                if project == "odip":
                    declaration = release.render(declaration, tag)
                Draft202012Validator(schema).validate(declaration)
                self.assertEqual(declaration["metadata"]["name"], project)
                self.assertEqual(declaration["metadata"]["project"], project)
                values = declaration["spec"]["configuration"]["values"]
                origin = f"https://web-{project}.apps.eseidinger.de"
                self.assertEqual(values["ODIP_API_URL"], origin)
                web, worker = declaration["spec"]["components"]
                self.assertEqual(
                    [c["name"] for c in (web, worker) if c.get("exposure") == "public"],
                    ["web"],
                )
                self.assertTrue(
                    all(
                        c["runtime"]["image"].endswith(":" + tag) for c in (web, worker)
                    )
                )
                self.assertNotIn("resources", declaration["spec"])
                self.assertNotIn("bindings", worker)
                self.assertIn(
                    {"dns": origin.removeprefix("https://"), "port": 443},
                    worker["outbound"],
                )
                self.assertEqual(
                    web["telemetry"]["metrics"],
                    {"port": "http", "path": "/actuator/prometheus"},
                )
                self.assertEqual(
                    web["health"]["readiness"]["path"], "/actuator/health/readiness"
                )
                self.assertEqual(worker["retryLimit"], 0)
                self.assertEqual(worker["concurrencyPolicy"], "Forbid")
                for c in (web, worker):
                    self.assertEqual(c["telemetry"]["tracing"], {"enabled": True})
                self.assertFalse(
                    any(
                        re.search(
                            r"PASS|SECRET|TOKEN|CREDENTIAL|PRIVATE|API_?KEY|AUTH",
                            key,
                            re.I,
                        )
                        for key in values
                    )
                )

    def test_policy_matches_pinned_schema_and_has_disjoint_routes(self):
        snapshot = json.loads(
            (KIT / "platform/upstream-inputs.schema.json").read_text()
        )
        policy = json.loads(
            (ROOT / "infrastructure/integration/odip-access-policy.json").read_text()
        )
        Draft202012Validator({**snapshot, "$ref": "#/$defs/PolicyCreate"}).validate(
            policy
        )

        def contains(match, path):
            return (
                path == match["path"]
                if "path" in match
                else path == match["pathPrefix"]
                or path.startswith(match["pathPrefix"].rstrip("/") + "/")
            )

        for index, left in enumerate(policy["routes"]):
            for right in policy["routes"][index + 1 :]:
                if set(left["match"]["methods"]) & set(right["match"]["methods"]):
                    lp = left["match"].get("path", left["match"].get("pathPrefix"))
                    rp = right["match"].get("path", right["match"].get("pathPrefix"))
                    self.assertFalse(
                        contains(left["match"], rp) or contains(right["match"], lp)
                    )

    def test_platform_policy_owns_role_checks_and_keeps_administration_separate(self):
        policy = json.loads(
            (ROOT / "infrastructure/integration/odip-access-policy.json").read_text()
        )

        def permitted(path, method, mode, group):
            for route in policy["routes"]:
                match = route["match"]
                matched = (
                    path == match["path"]
                    if "path" in match
                    else path == match["pathPrefix"]
                    or path.startswith(match["pathPrefix"].rstrip("/") + "/")
                )
                if matched and method in match["methods"]:
                    return (
                        route["authentication"]["mode"] == mode
                        and group in route["authorization"]["anyOfGroups"]
                    )
            return False

        for path, method in [
            ("/api/v1/dataset-grants/fixture", "PUT"),
            ("/api/v1/publication-retention", "PUT"),
            ("/api/data-sources", "POST"),
            ("/api/datasets", "POST"),
            ("/api/v1/operator-capabilities", "GET"),
            ("/api/v1/artifact-storage/raw/fixture/migrate", "POST"),
        ]:
            self.assertTrue(
                permitted(path, method, "browser-session", "dataset-operators")
            )
            for group in ("dataset-readers", "ingestion-workers"):
                self.assertFalse(permitted(path, method, "browser-session", group))
                self.assertFalse(permitted(path, method, "bearer-token", group))
        self.assertTrue(
            permitted(
                "/api/v1/datasets/fixture/versions/1.0.0",
                "GET",
                "bearer-token",
                "dataset-readers",
            )
        )
        self.assertFalse(
            permitted("/api/v1/datasets", "POST", "bearer-token", "dataset-readers")
        )
        self.assertTrue(
            permitted(
                "/api/pipeline-runs/claim-next",
                "POST",
                "bearer-token",
                "ingestion-workers",
            )
        )
        self.assertFalse(
            permitted(
                "/api/pipeline-runs/claim-next",
                "POST",
                "bearer-token",
                "dataset-readers",
            )
        )
        for route in policy["routes"]:
            if route["authentication"]["mode"] == "browser-session":
                self.assertEqual(
                    route["authorization"]["anyOfGroups"], ["dataset-operators"]
                )

    def test_workflow_guard_requires_separate_database_and_s3_bindings(self):
        workflow = (ROOT / ".github/workflows/platform-deploy.yml").read_text()
        guard = textwrap.dedent(
            workflow.split(
                "      - name: Check deployment descriptor\n        run: |\n", 1
            )[1].split("      - name:", 1)[0]
        )
        ids = [
            "94983c92-41c2-439c-887b-3a6b59509633",
            "59b4c8c3-6311-4ba8-b32c-218377cf25ec",
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts/render-release.py").write_bytes(
                (ROOT / "scripts/render-release.py").read_bytes()
            )
            for project, filename, ref in [
                (
                    "odip-test",
                    "infrastructure/deployments/application-test.json",
                    "refs/heads/main",
                ),
                (
                    "odip",
                    "infrastructure/deployments/application.json",
                    "refs/tags/v0.5.1",
                ),
            ]:
                for backend, bindings, passes in [
                    ("postgres", ids[:1], True),
                    ("s3", ids, True),
                    ("s3", ids[:1], False),
                    ("postgres", ids, False),
                    ("s3", [ids[0], ids[0]], False),
                    ("s3", [ids[0], "invalid-uuid"], False),
                    ("unknown", ids[:1], False),
                ]:
                    with self.subTest(
                        project=project, backend=backend, bindings=bindings
                    ):
                        declaration = json.loads((ROOT / filename).read_text())
                        declaration["spec"]["configuration"]["values"].update(
                            {
                                "ODIP_ARTIFACT_STORAGE_BACKEND": backend,
                                "ODIP_WORKER_BINDING_PREFIX": "ACCESS_TEST",
                            }
                        )
                        declaration["spec"]["components"][0]["bindings"] = [
                            {"bindingId": binding, "envPrefix": ""}
                            for binding in bindings
                        ]
                        path = root / filename
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(json.dumps(declaration))
                        env = dict(
                            os.environ,
                            PROJECT=project,
                            DESCRIPTOR=filename,
                            GITHUB_REF=ref,
                            RUNNER_TEMP=directory,
                            GITHUB_ENV=str(root / "github-env"),
                        )
                        result = subprocess.run(
                            ["bash", "-e", "-c", guard],
                            cwd=root,
                            env=env,
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(result.returncode == 0, passes, result.stderr)

    def test_workflow_guard_accepts_only_matching_ref_project_and_images(self):
        workflow = (ROOT / ".github/workflows/platform-deploy.yml").read_text()
        guard = workflow.split(
            "      - name: Check deployment descriptor\n        run: |\n", 1
        )[1].split("      - name:", 1)[0]
        guard = textwrap.dedent(guard)
        with tempfile.TemporaryDirectory() as directory:
            scripts = Path(directory) / "scripts"
            scripts.mkdir()
            (scripts / "render-release.py").write_bytes(
                (ROOT / "scripts/render-release.py").read_bytes()
            )
            for filename in (
                "infrastructure/deployments/application.json",
                "infrastructure/deployments/application-test.json",
            ):
                declaration = json.loads((ROOT / filename).read_text())
                declaration["spec"]["components"][0]["bindings"] = [
                    {
                        "bindingId": "94983c92-41c2-439c-887b-3a6b59509633",
                        "envPrefix": "",
                    }
                ]
                declaration["spec"]["configuration"]["values"][
                    "ODIP_WORKER_BINDING_PREFIX"
                ] = "ACCESS_TEST"
                # This fixture intentionally tests the single-binding PostgreSQL path.
                # S3 binding combinations are covered by the separate guard test.
                declaration["spec"]["configuration"]["values"][
                    "ODIP_ARTIFACT_STORAGE_BACKEND"
                ] = "postgres"
                (Path(directory) / filename).parent.mkdir(parents=True, exist_ok=True)
                (Path(directory) / filename).write_text(json.dumps(declaration))
            version = "0.4.1"
            for project, filename, ref, passes in (
                (
                    "odip-test",
                    "infrastructure/deployments/application-test.json",
                    "refs/heads/main",
                    True,
                ),
                (
                    "odip",
                    "infrastructure/deployments/application.json",
                    "refs/tags/v" + version,
                    True,
                ),
                (
                    "odip",
                    "infrastructure/deployments/application.json",
                    "refs/heads/main",
                    False,
                ),
                (
                    "odip-test",
                    "infrastructure/deployments/application-test.json",
                    "refs/tags/v" + version,
                    False,
                ),
                (
                    "odip",
                    "infrastructure/deployments/application.json",
                    "refs/tags/vlatest",
                    False,
                ),
                (
                    "odip-test",
                    "infrastructure/deployments/application.json",
                    "refs/heads/main",
                    False,
                ),
            ):
                with self.subTest(project=project, ref=ref, filename=filename):
                    env = dict(
                        os.environ,
                        PROJECT=project,
                        DESCRIPTOR=filename,
                        GITHUB_REF=ref,
                        RUNNER_TEMP=directory,
                        GITHUB_ENV=str(Path(directory) / "github-env"),
                    )
                    result = subprocess.run(
                        ["bash", "-e", "-c", guard],
                        cwd=directory,
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(result.returncode == 0, passes, result.stderr)

    def test_release_renderer_changes_only_image_versions(self):
        source = json.loads(
            (ROOT / "infrastructure/deployments/application.json").read_text()
        )
        original = json.loads(json.dumps(source))
        for version in ("0.4.1", "v1.2.3", "v2.0.0-rc.1"):
            with self.subTest(version=version):
                declaration = release.render(source, version)
                expected = json.loads(json.dumps(source))
                for component in expected["spec"]["components"]:
                    component["runtime"]["image"] = component["runtime"][
                        "image"
                    ].replace("__VERSION__", version.removeprefix("v"))
                self.assertEqual(declaration, expected)
                self.assertEqual(source, original)

    def test_release_renderer_rejects_invalid_versions_and_wrong_templates(self):
        source = json.loads(
            (ROOT / "infrastructure/deployments/application.json").read_text()
        )
        for version in (
            "latest",
            "main",
            "",
            "v1.2",
            "01.2.3",
            "1.2.3-01",
            "1.2.3+build",
            "1.2.3;id",
            "1.2.3-" + "x" * 128,
        ):
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.render(source, version)
        source["spec"]["components"][0]["runtime"]["image"] = "example/web:latest"
        with self.assertRaises(ValueError):
            release.render(source, "0.4.1")
        with self.assertRaises(ValueError):
            release.render(
                json.loads(
                    (
                        ROOT / "infrastructure/deployments/application-test.json"
                    ).read_text()
                ),
                "0.4.1",
            )

    def test_release_cli_emits_only_valid_json_and_preserves_template(self):
        path = ROOT / "infrastructure/deployments/application.json"
        before = path.read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/render-release.py"),
                "--version",
                "v0.4.1",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(
            json.loads(result.stdout), release.render(json.loads(before), "0.4.1")
        )
        self.assertEqual(path.read_bytes(), before)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/render-release.py"),
                "--version",
                "latest",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
