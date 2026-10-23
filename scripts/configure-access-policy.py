"""Preview or apply ODIP's access policy through devplat CLI v0.3.0.

The CLI owns authentication and HTTP. No platform writes occur without --apply.
Apply creates missing policy groups before saving the policy. It never approves
membership/service access or deploys applications.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "infrastructure/integration/odip-access-policy.json"
GROUPS = ROOT / "infrastructure/integration/groups.json"
POLICY_FIELDS = ("component", "defaultDecision", "identityAttributes", "routes")
CLI_VERSION = "0.3.0"
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class PolicyError(RuntimeError):
    """A safe error that never includes raw CLI output or credentials."""

    def __init__(self, message, exit_code=1):
        super().__init__(message)
        self.exit_code = exit_code


def platform_origin(value: str) -> str:
    try:
        parts = urlsplit(value)
        valid = (
            parts.scheme == "https"
            and parts.hostname
            and parts.username is None
            and parts.password is None
            and parts.path in ("", "/")
            and not parts.query
            and not parts.fragment
            and parts.port in (None, 443)
            and not any(char.isspace() for char in value)
        )
    except ValueError:
        valid = False
    if not valid:
        raise PolicyError(
            "Supply the Platform API HTTPS origin, without credentials, path, or query."
        )
    return value.rstrip("/")


class PlatformCLI:
    def __init__(
        self, origin=None, profile=None, *, executable="devplat", environment=None
    ):
        self.origin = platform_origin(origin) if origin else None
        if profile is not None and not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", profile
        ):
            raise PolicyError("Supply a valid devplat profile name.")
        self.profile = profile
        self.executable = executable
        self.environment = dict(os.environ if environment is None else environment)

    def _command(self, arguments):
        command = [self.executable, "--output", "json", "--quiet", "--no-color"]
        if self.profile:
            command += ["--profile", self.profile]
        if self.origin:
            command += ["--api-url", self.origin]
        return command + arguments

    def _run(
        self, command, *, body=None, timeout=60, missing_policy=False, version=False
    ):
        try:
            result = subprocess.run(
                command,
                input=json.dumps(body) if body is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=self.environment,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            raise PolicyError(
                "Install developer-platform-cli v0.3.0 and put devplat on PATH.", 2
            ) from None
        except subprocess.TimeoutExpired:
            raise PolicyError(
                "The CLI timed out. Any submitted operation continues; inspect the policy before retrying.",
                10,
            ) from None
        except (OSError, UnicodeError):
            raise PolicyError(
                "Unable to execute devplat safely. Inspect any submitted operation before retrying.",
                8,
            ) from None
        if result.returncode:
            # The CLI's machine error is on stderr, not stdout. Only this exact
            # absence permits creation; other 404 errors must not become writes.
            if missing_policy and result.returncode == 5:
                try:
                    error = json.loads(result.stderr)
                    if (
                        isinstance(error, dict)
                        and error.get("status") == 404
                        and error.get("detail") == "Access policy is not configured"
                    ):
                        return None
                except (ValueError, UnicodeError):
                    pass
            messages = {
                2: "Check CLI configuration. Select a profile and run devplat auth login, or securely supply PLATFORM_ACCESS_TOKEN.",
                3: "Authentication failed; sign in with devplat auth login or obtain a fresh administrator access token.",
                4: "Access denied; use a project administrator, not a deployment credential.",
                5: "The selected platform resource was not found.",
                6: "A version conflict occurred. Preview the current policy before applying again.",
                7: "The CLI or platform rejected the input. Check the policy template and application eligibility.",
                8: "The platform or identity provider is unavailable. A write may have been accepted; inspect it before retrying.",
                9: "Policy reconciliation failed. Inspect access operations; no automatic retry was made.",
                10: "Waiting stopped. The submitted operation is not cancelled; inspect it in the portal or rerun the preview.",
            }
            raise PolicyError(
                messages.get(
                    result.returncode,
                    "The CLI failed; inspect the platform before retrying.",
                ),
                result.returncode if 1 <= result.returncode <= 10 else 1,
            )
        if len(result.stdout.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise PolicyError("The CLI output exceeded the size limit.")
        if version:
            return result.stdout.strip()
        try:
            document = json.loads(result.stdout)
        except (ValueError, UnicodeError):
            raise PolicyError("The CLI returned invalid JSON.") from None
        if not isinstance(document, dict):
            raise PolicyError("The CLI returned an invalid resource.")
        return document

    def invoke(self, arguments, **kwargs):
        return self._run(self._command(arguments), **kwargs)

    def prepare(self):
        if self._run([self.executable, "--version"], version=True) != CLI_VERSION:
            raise PolicyError(
                "This script requires devplat CLI v0.3.0; install the reviewed release.",
                2,
            )
        if self.origin is None:
            profile = self.invoke(["profiles", "show"])
            self.origin = platform_origin(profile.get("api_url", ""))
        auth = self.invoke(["auth", "status"])
        if auth.get("source") == "deployment-credential-environment":
            raise PolicyError(
                "Deployment credentials cannot manage access policy. Use a human administrator CLI login or administrator access token.",
                4,
            )
        if auth.get("source") not in (
            "human-profile-session",
            "access-token-environment",
        ):
            raise PolicyError(
                "Sign in with devplat auth login or securely supply PLATFORM_ACCESS_TOKEN.",
                3,
            )
        if (
            auth.get("source") == "human-profile-session"
            and auth.get("persistent") is not True
        ):
            raise PolicyError(
                "No CLI login session is available. Run devplat auth login for the selected profile.",
                3,
            )

    def context(self, project):
        return self.invoke(["access", "context", "--project", project])

    def groups(self, project):
        return self.invoke(["access", "groups", "list", "--project", project])

    def group_create(self, project, group):
        return self.invoke(
            [
                "access",
                "groups",
                "create",
                "--project",
                project,
                "--file",
                "-",
                "--idempotency-key",
                f"{project}-{group['name']}",
            ],
            body=group,
        )

    def policy_get(self, project):
        return self.invoke(
            ["access", "policy", "get", "--project", project, "--application", project],
            missing_policy=True,
        )

    def policy_apply(self, project, policy, etag, timeout):
        arguments = [
            "access",
            "policy",
            "apply",
            "--project",
            project,
            "--application",
            project,
            "--file",
            "-",
            "--wait",
            "--timeout",
            str(timeout),
            "--poll-interval",
            "2",
        ]
        if etag is not None:
            arguments += ["--if-match", etag]
        # CLI v0.3.0 rejects "0". For creation use its native version handling.
        # Send only non-secret policy JSON via stdin; never persist a temp file.
        return self.invoke(arguments, body=policy, timeout=timeout + 45)


def resolve_policy(template: dict, groups: list) -> dict:
    policy = deepcopy(template)
    required = {
        group
        for route in policy["routes"]
        for group in route["authorization"]["anyOfGroups"]
    }
    resolved = {}
    for name in sorted(required):
        matches = [group for group in groups if group.get("name") == name]
        if len(matches) != 1:
            raise PolicyError(
                f"Expected exactly one existing application group named {name}."
            )
        group = matches[0]
        if group.get("state") != "active":
            raise PolicyError(f"Application group {name} is not active yet.")
        if not re.fullmatch(r"grp_[0-9a-f]{32}", group.get("id", "")):
            raise PolicyError(f"Application group {name} has an invalid stable ID.")
        resolved[name] = group["id"]
    for route in policy["routes"]:
        route["authorization"]["anyOfGroups"] = [
            resolved[name] for name in route["authorization"]["anyOfGroups"]
        ]
    return policy


def plan_groups(template, groups):
    definitions = json.loads(GROUPS.read_text())
    required = {
        name
        for route in template["routes"]
        for name in route["authorization"]["anyOfGroups"]
    }
    missing = []
    for name in sorted(required):
        matches = [group for group in groups if group.get("name") == name]
        if not matches:
            definitions_for_name = [
                group for group in definitions if group.get("name") == name
            ]
            if len(definitions_for_name) != 1:
                raise PolicyError(f"Expected exactly one group definition for {name}.")
            missing.append(definitions_for_name[0])
        elif (
            len(matches) != 1
            or matches[0].get("state") != "active"
            or not re.fullmatch(r"grp_[0-9a-f]{32}", matches[0].get("id", ""))
        ):
            raise PolicyError(
                f"Existing application group {name} is duplicate, inactive, or has an invalid stable ID."
            )
    return missing


def authorization_redacted(resource: dict | None) -> bool:
    return resource is not None and any(
        route.get("authorization") == "[REDACTED]"
        for route in resource.get("spec", {}).get("routes", [])
    )


def policy_matches(resource: dict, policy: dict, *, allow_redacted=False) -> bool:
    def normalize(value):
        if isinstance(value, dict):
            return {
                key: normalize(item) for key, item in value.items() if item is not None
            }
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    spec = resource.get("spec", {})
    observed = deepcopy({field: spec.get(field) for field in POLICY_FIELDS})
    if allow_redacted and isinstance(observed.get("routes"), list):
        # CLI v0.3.0 masks the entire authorization object as if it were a
        # credential. After a successful apply, compare only observable fields.
        # Never use this partial comparison to skip an update or infer equality.
        for route, desired in zip(observed["routes"], policy["routes"]):
            if route.get("authorization") == "[REDACTED]":
                route["authorization"] = desired["authorization"]
    return normalize(observed) == normalize(policy)


def wait_for_active(
    cli, project, policy, timeout, *, clock=time.monotonic, sleep=time.sleep
):
    """Observe an already pending policy without submitting another operation."""
    deadline = clock() + timeout
    while True:
        resource = cli.policy_get(project)
        if resource is None or not policy_matches(resource, policy):
            raise PolicyError(
                "The policy changed while waiting. Inspect the current policy; no further write was made."
            )
        if resource.get("state") == "active":
            return resource
        if resource.get("state") != "provisioning":
            raise PolicyError(
                "Policy provisioning did not become active. Inspect access operations; no automatic retry was made."
            )
        remaining = deadline - clock()
        if remaining <= 0:
            raise PolicyError(
                "Timed out waiting for activation. The operation is not cancelled; inspect it or rerun the preview.",
                10,
            )
        sleep(min(2, remaining))


def configure(cli, project, *, apply=False, timeout=120, output=print):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", project):
        raise PolicyError("Supply a valid project name.")
    template = json.loads(POLICY.read_text())
    context = cli.context(project)
    if context.get("project") != project or context.get("application") != project:
        raise PolicyError(
            "The application-access context does not match the selected project."
        )
    if not context.get("eligible") or context.get("component") != template["component"]:
        raise PolicyError(
            "Deploy an eligible v1alpha2 application with public component web before configuring this policy."
        )
    if context.get("permissions", {}).get("manage") is not True:
        raise PolicyError(
            "Project-administrator authority is required to configure application access."
        )
    listed = cli.groups(project)
    if not isinstance(listed.get("items"), list) or any(
        not isinstance(g, dict) for g in listed["items"]
    ):
        raise PolicyError("The CLI returned an invalid group list.")
    missing = plan_groups(template, listed["items"])
    # Preview retains names for groups that have not been created; never invent IDs.
    policy = (
        deepcopy(template) if missing else resolve_policy(template, listed["items"])
    )
    existing = cli.policy_get(project)
    etag = existing.get("etag") if existing is not None else None
    if existing is not None and (
        not isinstance(etag, str) or not re.fullmatch(r'"[1-9][0-9]*"', etag)
    ):
        raise PolicyError(
            "The current policy has no valid CLI ETag; refusing an unguarded update."
        )
    unchanged = (
        not missing and existing is not None and policy_matches(existing, policy)
    )
    action = (
        "unchanged" if unchanged else "replace" if existing is not None else "create"
    )
    output(
        json.dumps(
            {
                "platform": getattr(cli, "origin", None),
                "project": project,
                "action": action,
                "currentVersion": etag,
                "currentState": existing.get("state") if existing else None,
                "currentGroupsRedacted": authorization_redacted(existing),
                "groupsToCreate": missing,
                "policyGroupsResolved": not missing,
                "policy": policy,
            },
            indent=2,
        )
    )
    if not apply:
        output(
            "Preview only: no platform writes. Use --apply to create missing groups and save this complete policy."
        )
        return
    if (
        not unchanged
        and existing is not None
        and existing.get("state") not in ("active", "failed")
    ):
        raise PolicyError("Wait for the pending policy operation before replacing it.")
    if missing:
        for group in missing:
            output(f"Creating application group {group['name']} through devplat.")
            cli.group_create(project, group)
        listed = cli.groups(project)
        if not isinstance(listed.get("items"), list) or any(
            not isinstance(g, dict) for g in listed["items"]
        ):
            raise PolicyError("The CLI returned an invalid group list after creation.")
        policy = resolve_policy(template, listed["items"])
    if unchanged:
        if existing.get("state") == "active":
            output("Policy is already active and unchanged; no write made.")
            return
        if existing.get("state") != "provisioning":
            raise PolicyError(
                "The unchanged policy is not active. Inspect and retry its failed operation through the platform."
            )
        resource = wait_for_active(cli, project, policy, timeout)
    else:
        if existing is not None and existing.get("state") not in ("active", "failed"):
            raise PolicyError(
                "Wait for the pending policy operation before replacing it."
            )
        output(
            "Applying through devplat and waiting for activation; no automatic write retry will be made."
        )
        resource = cli.policy_apply(project, policy, etag, timeout)
        if (
            not policy_matches(resource, policy, allow_redacted=True)
            or resource.get("state") != "active"
        ):
            raise PolicyError(
                "The CLI did not confirm the requested policy as active. Inspect it before proceeding."
            )
    output(
        f"Policy active: {len(policy['routes'])} routes, resource version {resource.get('version')}."
    )
    if authorization_redacted(resource):
        output(
            "CLI v0.3.0 redacts group assignments. Apply succeeded and visible fields match, but group assignments cannot be independently verified through CLI read-back."
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform-url",
        default=os.getenv("PLATFORM_API_URL"),
        help="Platform HTTPS origin; otherwise use the CLI profile",
    )
    parser.add_argument(
        "--profile",
        help="Existing devplat profile; otherwise use its active profile/environment authentication",
    )
    parser.add_argument("--project", default="odip")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Create missing groups, replace the COMPLETE policy and wait for activation",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Authenticated preview only (the default)",
    )
    parser.add_argument("--wait-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.wait_seconds <= 600:
            raise PolicyError("--wait-seconds must be between 1 and 600.")
        cli = PlatformCLI(args.platform_url, args.profile)
        cli.prepare()
        configure(cli, args.project, apply=args.apply, timeout=args.wait_seconds)
        return 0
    except (PolicyError, OSError, ValueError) as error:
        message = (
            str(error)
            if isinstance(error, PolicyError)
            else "Unable to read local policy or CLI configuration."
        )
        print("Error: " + message, file=sys.stderr)
        return error.exit_code if isinstance(error, PolicyError) else 1
    except KeyboardInterrupt:
        print(
            "Interrupted. Any submitted policy operation continues; inspect it before retrying.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
