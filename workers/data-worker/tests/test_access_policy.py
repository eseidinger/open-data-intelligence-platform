import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator
from odip_worker.contract import KIT

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "configure_access_policy", ROOT / "scripts/configure-access-policy.py"
)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
TEMPLATE = json.loads(script.POLICY.read_text())
GROUPS = [
    {"name": name, "id": "grp_" + char * 32, "state": "active"}
    for name, char in [
        ("dataset-operators", "a"),
        ("dataset-readers", "b"),
        ("ingestion-workers", "c"),
    ]
]
POLICY = script.resolve_policy(TEMPLATE, GROUPS)


def resource(state="active", policy=None, version=3):
    spec = deepcopy(policy or POLICY)
    for route in spec["routes"]:
        route["match"].setdefault("path", None)
        route["match"].setdefault("pathPrefix", None)
    return {
        "state": state,
        "version": version,
        "etag": '"' + str(version) + '"',
        "spec": {**spec, "host": "web-odip.apps.test", "revisionId": "revision"},
    }


class FakeCLI:
    def __init__(self, existing=None):
        self.existing = existing
        self.group_items = deepcopy(GROUPS)
        self.context_document = {
            "project": "odip",
            "application": "odip",
            "eligible": True,
            "component": "web",
            "permissions": {"manage": True},
        }
        self.calls = []

    def context(self, project):
        self.calls.append(("context", project, {}))
        return self.context_document

    def groups(self, project):
        self.calls.append(("groups", project, {}))
        return {"items": self.group_items}

    def group_create(self, project, group):
        self.calls.append(("group create", project, {"body": group}))
        created = deepcopy(next(g for g in GROUPS if g["name"] == group["name"]))
        self.group_items.append(created)
        return created

    def policy_get(self, project):
        self.calls.append(("policy get", project, {}))
        return self.existing

    def policy_apply(self, project, policy, etag, timeout):
        self.calls.append(
            (
                "policy apply",
                project,
                {"body": policy, "etag": etag, "timeout": timeout},
            )
        )
        self.existing = resource(policy=policy, version=4)
        return self.existing


def completed(document=None, *, code=0, stderr="", stdout=None):
    return subprocess.CompletedProcess(
        ["devplat"],
        code,
        stdout=stdout if stdout is not None else json.dumps(document),
        stderr=stderr,
    )


class AccessPolicyTests(unittest.TestCase):
    def test_resolves_active_named_groups_and_preserves_pinned_policy_schema(self):
        snapshot = json.loads(
            (KIT / "platform/upstream-inputs.schema.json").read_text()
        )
        Draft202012Validator({**snapshot, "$ref": "#/$defs/PolicyCreate"}).validate(
            POLICY
        )
        for before, after in zip(TEMPLATE["routes"], POLICY["routes"]):
            self.assertEqual(before["match"], after["match"])
            self.assertEqual(before["authentication"], after["authentication"])
            self.assertRegex(
                after["authorization"]["anyOfGroups"][0], r"^grp_[abc]{32}$"
            )
        self.assertEqual(
            TEMPLATE["routes"][0]["authorization"]["anyOfGroups"], ["dataset-readers"]
        )

    def test_missing_duplicate_pending_or_malformed_groups_fail(self):
        pending = deepcopy(GROUPS)
        pending[0]["state"] = "provisioning"
        invalid = deepcopy(GROUPS)
        invalid[0]["id"] = "grp_invalid"
        for groups in (GROUPS[1:], GROUPS + [GROUPS[0]], pending, invalid):
            with self.subTest(groups=groups), self.assertRaises(script.PolicyError):
                script.resolve_policy(TEMPLATE, groups)

    def test_default_preview_uses_only_cli_reads(self):
        cli = FakeCLI()
        output = []
        script.configure(cli, "odip", output=output.append)
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))
        self.assertEqual(json.loads(output[0])["action"], "create")
        self.assertIn("no platform writes", output[-1])

    def test_creation_uses_cli_native_version_handling_and_wait(self):
        cli = FakeCLI()
        output = []
        script.configure(cli, "odip", apply=True, output=output.append)
        writes = [
            (project, kwargs)
            for command, project, kwargs in cli.calls
            if command == "policy apply"
        ]
        self.assertEqual(
            writes, [("odip", {"body": POLICY, "etag": None, "timeout": 120})]
        )
        self.assertIn("Policy active:", output[-1])

    def test_existing_policy_is_replaced_using_exact_cli_etag(self):
        different = deepcopy(POLICY)
        different["routes"] = different["routes"][:1]
        cli = FakeCLI(resource(policy=different))
        script.configure(cli, "odip", apply=True, output=lambda _: None)
        writes = [
            kwargs for command, _, kwargs in cli.calls if command == "policy apply"
        ]
        self.assertEqual(writes, [{"body": POLICY, "etag": '"3"', "timeout": 120}])

    def test_unchanged_active_policy_is_noop_despite_server_derived_fields(self):
        cli = FakeCLI(resource())
        script.configure(cli, "odip", apply=True, output=lambda _: None)
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))

    def test_comparison_accepts_null_match_fields_but_not_real_changes(self):
        self.assertTrue(script.policy_matches(resource(), POLICY))
        changed = resource()
        changed["spec"]["routes"][0]["match"]["methods"].append("POST")
        self.assertFalse(script.policy_matches(changed, POLICY))

    def test_redacted_authorization_is_not_treated_as_an_identical_policy(self):
        redacted = resource()
        for route in redacted["spec"]["routes"]:
            route["authorization"] = "[REDACTED]"
        self.assertTrue(script.authorization_redacted(redacted))
        self.assertFalse(script.policy_matches(redacted, POLICY))
        self.assertTrue(script.policy_matches(redacted, POLICY, allow_redacted=True))
        cli = FakeCLI(redacted)
        output = []
        script.configure(cli, "odip", output=output.append)
        self.assertEqual(json.loads(output[0])["action"], "replace")
        self.assertTrue(json.loads(output[0])["currentGroupsRedacted"])
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))
        script.configure(cli, "odip", apply=True, output=lambda _: None)
        self.assertEqual(
            len([command for command, _, _ in cli.calls if command == "policy apply"]),
            1,
        )

    def test_redacted_readback_reports_limits_but_visible_changes_still_fail(self):
        redacted = resource()
        for route in redacted["spec"]["routes"]:
            route["authorization"] = "[REDACTED]"
        cli = FakeCLI()
        cli.policy_apply = Mock(return_value=redacted)
        output = []
        script.configure(cli, "odip", apply=True, output=output.append)
        self.assertIn("cannot be independently verified", output[-1])
        redacted["spec"]["routes"][0]["authentication"]["mode"] = "browser-session"
        self.assertFalse(script.policy_matches(redacted, POLICY, allow_redacted=True))
        with self.assertRaisesRegex(script.PolicyError, "did not confirm"):
            script.configure(cli, "odip", apply=True, output=lambda _: None)

    def test_unchanged_provisioning_policy_waits_without_resubmitting(self):
        cli = FakeCLI(resource("provisioning"))
        with patch.object(script, "wait_for_active", return_value=resource()) as wait:
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        wait.assert_called_once_with(cli, "odip", POLICY, 120)
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))

    def test_failed_unchanged_policy_requires_explicit_platform_retry(self):
        cli = FakeCLI(resource("failed"))
        with self.assertRaisesRegex(script.PolicyError, "retry its failed operation"):
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))

    def test_missing_etag_ineligible_context_or_missing_authority_block_writes(self):
        for change in ("etag", "component", "eligible", "manage", "project", "groups"):
            with self.subTest(change=change):
                cli = FakeCLI(resource())
                if change == "etag":
                    cli.existing.pop("etag")
                elif change == "component":
                    cli.context_document["component"] = "api"
                elif change == "eligible":
                    cli.context_document["eligible"] = False
                elif change == "manage":
                    cli.context_document["permissions"]["manage"] = False
                elif change == "project":
                    cli.context_document["project"] = "other"
                else:
                    cli.group_items.append(deepcopy(cli.group_items[0]))
                with self.assertRaises(script.PolicyError):
                    script.configure(cli, "odip", apply=True, output=lambda _: None)
                self.assertTrue(
                    all(command != "policy apply" for command, _, _ in cli.calls)
                )

    def test_pending_different_policy_cannot_be_overwritten(self):
        different = deepcopy(POLICY)
        different["routes"] = different["routes"][:1]
        cli = FakeCLI(resource("provisioning", different))
        with self.assertRaisesRegex(script.PolicyError, "pending policy operation"):
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        self.assertTrue(all(command != "policy apply" for command, _, _ in cli.calls))

    def test_apply_does_not_claim_success_for_changed_or_inactive_policy(self):
        for response in (
            resource("provisioning"),
            resource(policy={**POLICY, "routes": POLICY["routes"][:1]}),
        ):
            cli = FakeCLI()
            cli.policy_apply = Mock(return_value=response)
            with self.assertRaisesRegex(script.PolicyError, "did not confirm"):
                script.configure(cli, "odip", apply=True, output=lambda _: None)
            cli.policy_apply.assert_called_once()

    def test_cli_conflicts_and_uncertain_writes_are_not_retried(self):
        cli = FakeCLI()
        cli.policy_apply = Mock(side_effect=script.PolicyError("Conflict", 6))
        with self.assertRaises(script.PolicyError):
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        cli.policy_apply.assert_called_once()

    def test_wait_polls_until_active_and_has_bounded_timeout(self):
        cli = Mock()
        cli.policy_get.side_effect = [resource("provisioning"), resource()]
        sleep = Mock()
        self.assertEqual(
            script.wait_for_active(
                cli, "odip", POLICY, 120, clock=lambda: 0, sleep=sleep
            )["state"],
            "active",
        )
        sleep.assert_called_once_with(2)
        cli.policy_get.side_effect = None
        cli.policy_get.return_value = resource("provisioning")
        with self.assertRaisesRegex(script.PolicyError, "not cancelled"):
            script.wait_for_active(
                cli, "odip", POLICY, 1, clock=Mock(side_effect=[0, 2]), sleep=Mock()
            )

    def test_wait_detects_failed_removed_or_concurrently_changed_policy(self):
        cli = Mock()
        different = deepcopy(POLICY)
        different["routes"] = different["routes"][:1]
        for result in (resource("failed"), resource(policy=different), None):
            cli.policy_get.return_value = result
            with self.assertRaises(script.PolicyError):
                script.wait_for_active(cli, "odip", POLICY, 120)

    def test_origin_profile_and_project_reject_unsafe_values(self):
        for origin in (
            "http://platform.test",
            "https://user:password@platform.test",
            "https://@platform.test",
            "https://platform.test/api",
            "https://platform.test?token=secret",
            "https://platform.test:8443",
        ):
            with self.subTest(origin=origin), self.assertRaises(script.PolicyError):
                script.PlatformCLI(origin)
        with self.assertRaises(script.PolicyError):
            script.PlatformCLI(profile="--insecure")
        self.assertEqual(
            script.platform_origin("https://platform.test/"), "https://platform.test"
        )
        cli = FakeCLI()
        with self.assertRaises(script.PolicyError):
            script.configure(cli, "../odip")
        self.assertEqual(cli.calls, [])

    def test_commands_use_machine_output_profile_and_https_origin(self):
        cli = script.PlatformCLI(
            "https://platform.test",
            "lab",
            environment={"PLATFORM_ACCESS_TOKEN": "sensitive-token"},
        )
        with patch.object(
            script.subprocess, "run", return_value=completed({"items": GROUPS})
        ) as run:
            self.assertEqual(cli.groups("odip"), {"items": GROUPS})
        command = run.call_args.args[0]
        self.assertEqual(
            command,
            [
                "devplat",
                "--output",
                "json",
                "--quiet",
                "--no-color",
                "--profile",
                "lab",
                "--api-url",
                "https://platform.test",
                "access",
                "groups",
                "list",
                "--project",
                "odip",
            ],
        )
        self.assertNotIn("sensitive-token", " ".join(command))
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(
            run.call_args.kwargs["env"]["PLATFORM_ACCESS_TOKEN"], "sensitive-token"
        )

    def test_preview_lists_missing_groups_without_writes_or_invented_ids(self):
        cli = FakeCLI()
        cli.group_items = []
        output = []
        script.configure(cli, "odip", output=output.append)
        plan = json.loads(output[0])
        self.assertEqual(
            {g["name"] for g in plan["groupsToCreate"]}, {g["name"] for g in GROUPS}
        )
        self.assertFalse(plan["policyGroupsResolved"])
        self.assertEqual(plan["policy"], TEMPLATE)
        self.assertFalse(
            any(
                command in ("group create", "policy apply")
                for command, _, _ in cli.calls
            )
        )

    def test_apply_creates_only_missing_groups_before_resolving_policy_for_either_project(
        self,
    ):
        for project in ("odip", "odip-test"):
            cli = FakeCLI()
            cli.context_document.update(project=project, application=project)
            cli.group_items = deepcopy(GROUPS[:1])
            script.configure(cli, project, apply=True, output=lambda _: None)
            created = [
                (target, kw["body"]["name"])
                for command, target, kw in cli.calls
                if command == "group create"
            ]
            self.assertEqual(
                created, [(project, "dataset-readers"), (project, "ingestion-workers")]
            )
            writes = [kw for command, _, kw in cli.calls if command == "policy apply"]
            self.assertEqual(writes[0]["body"], POLICY)
            cli.calls.clear()
            script.configure(cli, project, apply=True, output=lambda _: None)
            self.assertFalse(
                any(
                    command in ("group create", "policy apply")
                    for command, _, _ in cli.calls
                )
            )

    def test_failed_group_creation_is_not_retried_and_blocks_policy_apply(self):
        cli = FakeCLI()
        cli.group_items = []
        cli.group_create = Mock(side_effect=script.PolicyError("Creation failed", 8))
        with self.assertRaises(script.PolicyError):
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        cli.group_create.assert_called_once()
        self.assertFalse(any(command == "policy apply" for command, _, _ in cli.calls))

    def test_invalid_existing_group_blocks_all_group_and_policy_writes(self):
        cli = FakeCLI()
        cli.group_items = [deepcopy(GROUPS[0])]
        cli.group_items[0]["state"] = "revoked"
        with self.assertRaises(script.PolicyError):
            script.configure(cli, "odip", apply=True, output=lambda _: None)
        self.assertFalse(
            any(
                command in ("group create", "policy apply")
                for command, _, _ in cli.calls
            )
        )

    def test_group_creation_uses_json_stdin_and_project_specific_idempotency(self):
        cli = script.PlatformCLI("https://platform.test", environment={})
        group = {"name": "dataset-operators", "displayName": "ODIP dataset operators"}
        for project in ("odip", "odip-test"):
            with patch.object(
                script.subprocess, "run", return_value=completed(GROUPS[0])
            ) as run:
                cli.group_create(project, group)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--file") + 1], "-")
            self.assertEqual(command[command.index("--project") + 1], project)
            self.assertEqual(
                command[command.index("--idempotency-key") + 1],
                project + "-dataset-operators",
            )
            self.assertEqual(json.loads(run.call_args.kwargs["input"]), group)

    def test_apply_passes_policy_via_stdin_and_delegates_wait_and_etag(self):
        cli = script.PlatformCLI("https://platform.test", environment={})
        for etag in (None, '"3"'):
            with (
                self.subTest(etag=etag),
                patch.object(
                    script.subprocess, "run", return_value=completed(resource())
                ) as run,
            ):
                cli.policy_apply("odip", POLICY, etag, 120)
                command = run.call_args.args[0]
                self.assertEqual(command[command.index("--file") + 1], "-")
                self.assertIn("--wait", command)
                self.assertEqual(command[command.index("--timeout") + 1], "120")
                self.assertEqual(run.call_args.kwargs["timeout"], 165)
                self.assertEqual(json.loads(run.call_args.kwargs["input"]), POLICY)
                if etag:
                    self.assertEqual(command[command.index("--if-match") + 1], etag)
                else:
                    self.assertNotIn("--if-match", command)

    def test_only_explicit_cli_policy_absence_is_treated_as_create(self):
        cli = script.PlatformCLI("https://platform.test", environment={})
        for status, detail in (
            (404, "Unknown project"),
            (403, "Access policy is not configured"),
            (404, "Access policy is not configured"),
        ):
            with patch.object(
                script.subprocess,
                "run",
                return_value=completed(
                    code=5, stderr=json.dumps({"status": status, "detail": detail})
                ),
            ):
                if status == 404 and detail == "Access policy is not configured":
                    self.assertIsNone(cli.policy_get("odip"))
                else:
                    with self.assertRaises(script.PolicyError):
                        cli.policy_get("odip")

    def test_cli_errors_preserve_exit_codes_without_leaking_output(self):
        cli = script.PlatformCLI("https://platform.test", environment={})
        for code in range(2, 11):
            with (
                self.subTest(code=code),
                patch.object(
                    script.subprocess,
                    "run",
                    return_value=completed(
                        code=code, stderr="sensitive-token", stdout="sensitive-token"
                    ),
                ) as run,
            ):
                with self.assertRaises(script.PolicyError) as caught:
                    cli.policy_apply("odip", POLICY, '"3"', 120)
                self.assertEqual(caught.exception.exit_code, code)
                self.assertNotIn("sensitive-token", str(caught.exception))
                run.assert_called_once()

    def test_missing_cli_timeout_and_invalid_json_are_safe(self):
        cli = script.PlatformCLI("https://platform.test", environment={})
        for error, code in [
            (FileNotFoundError("sensitive-token"), 2),
            (subprocess.TimeoutExpired(["sensitive-token"], 1), 10),
        ]:
            with patch.object(script.subprocess, "run", side_effect=error):
                with self.assertRaises(script.PolicyError) as caught:
                    cli.context("odip")
                self.assertEqual(caught.exception.exit_code, code)
                self.assertNotIn("sensitive-token", str(caught.exception))
        for stdout in ("sensitive-token", "[]", "x" * (script.MAX_OUTPUT_BYTES + 1)):
            with patch.object(
                script.subprocess, "run", return_value=completed(stdout=stdout)
            ):
                with self.assertRaises(script.PolicyError):
                    cli.context("odip")

    def test_prepare_checks_reviewed_version_and_delegates_authentication(self):
        cli = script.PlatformCLI("https://platform.test", "lab", environment={})
        with patch.object(
            script.subprocess,
            "run",
            side_effect=[
                completed(stdout="0.3.0\n"),
                completed({"source": "human-profile-session", "persistent": True}),
            ],
        ) as run:
            cli.prepare()
        self.assertEqual(run.call_args_list[0].args[0], ["devplat", "--version"])
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["auth", "status"])
        with patch.object(
            script.subprocess, "run", return_value=completed(stdout="0.1.0\n")
        ) as run:
            with self.assertRaisesRegex(script.PolicyError, "v0.3.0"):
                cli.prepare()
            run.assert_called_once()

    def test_prepare_uses_profile_origin_and_rejects_missing_session_or_deployment_auth(
        self,
    ):
        cli = script.PlatformCLI(profile="lab", environment={})
        with patch.object(
            script.subprocess,
            "run",
            side_effect=[
                completed(stdout="0.3.0\n"),
                completed({"api_url": "https://platform.test"}),
                completed({"source": "access-token-environment"}),
            ],
        ):
            cli.prepare()
        self.assertEqual(cli.origin, "https://platform.test")
        for auth in (
            {"source": "deployment-credential-environment"},
            {"source": "human-profile-session", "persistent": False},
            {"source": "unknown"},
        ):
            cli = script.PlatformCLI("https://platform.test", environment={})
            with patch.object(
                script.subprocess,
                "run",
                side_effect=[completed(stdout="0.3.0\n"), completed(auth)],
            ):
                with self.assertRaises(script.PolicyError):
                    cli.prepare()
        cli = script.PlatformCLI(environment={})
        with patch.object(
            script.subprocess,
            "run",
            side_effect=[
                completed(stdout="0.3.0\n"),
                completed({"api_url": "http://platform.test"}),
            ],
        ) as run:
            with self.assertRaises(script.PolicyError):
                cli.prepare()
            self.assertEqual(run.call_count, 2)

    def test_main_uses_cli_profile_and_defaults_to_preview_without_token_prompt(self):
        with (
            patch.dict(script.os.environ, {}, clear=True),
            patch.object(script, "PlatformCLI") as client,
            patch.object(script, "configure") as configure,
        ):
            self.assertEqual(script.main(["--profile", "lab"]), 0)
            client.assert_called_once_with(None, "lab")
            client.return_value.prepare.assert_called_once()
            configure.assert_called_once_with(
                client.return_value, "odip", apply=False, timeout=120
            )

    def test_main_preserves_cli_exit_code_and_rejects_invalid_wait(self):
        errors = io.StringIO()
        with (
            patch.object(script, "PlatformCLI") as client,
            contextlib.redirect_stderr(errors),
        ):
            client.return_value.prepare.side_effect = script.PolicyError(
                "Sign in again.", 3
            )
            self.assertEqual(script.main(["--profile", "lab"]), 3)
        self.assertIn("Sign in again", errors.getvalue())
        with (
            patch.object(script, "PlatformCLI") as client,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(script.main(["--wait-seconds", "0"]), 1)
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
