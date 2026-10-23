"""Preview or provision ODIP's named PostgreSQL resource and web binding via devplat.

Use --apply to create missing resources. Repeated runs reuse matching resources;
this script never migrates data, changes quotas, revokes access, or deploys.
"""

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "infrastructure/integration/odip-postgresql.json"
CLI_VERSION = "0.3.0"


class StorageError(RuntimeError):
    pass


class PlatformCLI:
    def __init__(self, profile=None):
        self.profile = profile
        self.command = ["devplat", "--output", "json", "--quiet", "--no-color"]
        if profile:
            self.command += ["--profile", profile]

    def invoke(self, arguments, body=None, *, timeout=60, allow_list=False):
        try:
            result = subprocess.run(
                self.command + arguments,
                input=json.dumps(body) if body is not None else None,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise StorageError(
                "Cannot complete devplat command. Inspect storage before rerunning; submitted writes may continue."
            ) from None
        if result.returncode:
            # Do not echo raw CLI output, which may contain authentication data.
            login = shlex.join(
                ["devplat"]
                + (["--profile", self.profile] if self.profile else [])
                + ["auth", "login"]
            )
            if result.returncode == 3:
                raise StorageError(
                    f"Authentication failed (devplat exit code 3). Run `{login}` and complete browser sign-in, then rerun setup. "
                    "If PLATFORM_ACCESS_TOKEN is set, replace the expired/invalid token or unset it to use your profile login."
                )
            if result.returncode == 4:
                raise StorageError(
                    "Access denied (devplat exit code 4). Use a project-administrator identity for the selected project; deployment credentials cannot manage storage."
                )
            raise StorageError(
                f"devplat exited with code {result.returncode}. Check CLI login/keyring or PLATFORM_ACCESS_TOKEN, "
                "project-administrator permissions, and platform availability. Inspect storage before rerunning."
            )
        try:
            document = json.loads(result.stdout)
        except ValueError:
            raise StorageError(
                "devplat returned invalid JSON; inspect storage before rerunning."
            ) from None
        if not isinstance(document, dict) and not (
            allow_list and isinstance(document, list)
        ):
            raise StorageError("devplat returned an invalid storage response.")
        return document


def items(document, key):
    value = document.get(key)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise StorageError(f"devplat returned an invalid {key} list.")
    return value


def identity(row, key):
    try:
        return str(UUID(row[key]))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise StorageError(f"Storage response has no valid {key} UUID.") from None


def validate_resource(row, project, desired):
    identity(row, "resource_id")
    if (
        row.get("owner_project") != project
        or row.get("name") != desired["name"]
        or row.get("provider") != "postgresql"
        or row.get("state") != "active"
        or row.get("quota_bytes") != desired["quota_bytes"]
        or row.get("extensions", []) != desired["extensions"]
    ):
        raise StorageError(
            "Existing resource does not match the requested active PostgreSQL configuration; review it manually."
        )


def validate_binding(row, project, resource_id):
    identity(row, "grant_id")
    if (
        row.get("resource_id") != resource_id
        or row.get("consumer_project") != project
        or row.get("component") != "web"
        or row.get("kind") != "binding"
        or row.get("mode") != "read-write"
        or row.get("state") != "active"
    ):
        raise StorageError(
            "Existing binding does not match approved read-write access for web; review it manually."
        )


def wait_active(read, validate, timeout, *, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while True:
        row = read()
        validate(row)
        if row.get("error_code") or row.get("observed_state") == "failed":
            raise StorageError(
                "Storage reconciliation reported a failure. Inspect it in the platform before rerunning."
            )
        if row.get("observed_state") == "active":
            return row
        if clock() >= deadline:
            raise StorageError(
                "Timed out waiting for storage. Provisioning continues; rerun to inspect and reuse it."
            )
        sleep(min(2, max(0, deadline - clock())))


def setup(cli, project, desired, *, apply=False, timeout=180):
    if not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,30}[a-z0-9])?", project):
        raise StorageError("Supply a valid project slug of at most 32 characters.")
    context = cli.invoke(["stores", "context", "--project", project])
    if context.get("project") != project or context.get("manage") is not True:
        raise StorageError(
            "Use an existing project and a project-administrator login; deployment credentials cannot set up stores."
        )
    if not any(
        p.get("id") == "postgresql" and p.get("enabled") is True
        for p in context.get("providers", [])
    ):
        raise StorageError("PostgreSQL is not enabled on this platform.")
    resources = items(cli.invoke(["stores", "list", "--project", project]), "resources")
    matches = [row for row in resources if row.get("name") == desired["name"]]
    if len(matches) > 1:
        raise StorageError(
            "Multiple resources match the storage name; review them manually."
        )
    resource = matches[0] if matches else None
    if resource:
        validate_resource(resource, project, desired)
    # Read bindings before any write so unexpected access cannot create an orphan store.
    bindings = items(
        cli.invoke(["stores", "bindings", "list", "--project", project]), "bindings"
    )
    candidates = [
        row
        for row in bindings
        if row.get("component") == "web" and row.get("state") in ("pending", "active")
    ]
    if len(candidates) > 1 or (
        candidates
        and (
            not resource or candidates[0].get("resource_id") != resource["resource_id"]
        )
    ):
        raise StorageError(
            "web already has a different or ambiguous storage binding; review it manually."
        )
    binding = candidates[0] if candidates else None
    if binding:
        validate_binding(binding, project, resource["resource_id"])
    if not apply:
        return {
            "project": project,
            "apply": False,
            "resource": desired,
            "resource_action": "reuse" if resource else "create",
            "binding_action": "reuse" if binding else "request",
            "component": "web",
            "resource_id": resource["resource_id"] if resource else None,
            "binding_id": binding["grant_id"] if binding else None,
        }
    if resource is None:
        resource = cli.invoke(
            ["stores", "create", "--project", project, "--file", "-"], desired
        )
    resource_id = identity(resource, "resource_id")
    wait_active(
        lambda: cli.invoke(["stores", "get", resource_id]),
        lambda row: validate_resource(row, project, desired),
        timeout,
    )
    if binding is None:
        binding = cli.invoke(
            ["stores", "bindings", "request", "--project", project, "--file", "-"],
            {"resource_id": resource_id, "component": "web", "mode": "read-write"},
        )
    validate_binding(binding, project, resource_id)
    binding_id = identity(binding, "grant_id")

    def read_binding():
        rows = items(
            cli.invoke(["stores", "bindings", "list", "--project", project]), "bindings"
        )
        found = [row for row in rows if row.get("grant_id") == binding_id]
        if len(found) != 1:
            raise StorageError(
                "The requested binding disappeared; inspect storage before rerunning."
            )
        return found[0]

    wait_active(
        read_binding, lambda row: validate_binding(row, project, resource_id), timeout
    )
    return {
        "project": project,
        "apply": True,
        "resource_id": resource_id,
        "binding_id": binding_id,
        "component": "web",
        "observed_state": "active",
        "ODIP_DATABASE_BINDING_ID": binding_id,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", help="Existing devplat profile; otherwise use the active profile"
    )
    parser.add_argument("--project", default="odip")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Create missing storage and wait for activation",
    )
    mode.add_argument(
        "--dry-run", action="store_true", help="Authenticated preview (default)"
    )
    parser.add_argument(
        "--quota-bytes",
        type=int,
        help="Allocation for a new resource; existing quotas are never modified",
    )
    parser.add_argument(
        "--update-descriptor",
        type=Path,
        help="With --apply, save the web binding UUID in this project's deployment descriptor",
    )
    parser.add_argument("--wait-seconds", type=int, default=180)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.wait_seconds <= 600:
            raise StorageError("--wait-seconds must be between 1 and 600.")
        descriptor = None
        if args.update_descriptor:
            if not args.apply:
                raise StorageError("--update-descriptor requires --apply.")
            descriptor = json.loads(args.update_descriptor.read_text())
            if (
                descriptor.get("metadata", {}).get("name") != args.project
                or descriptor["metadata"].get("project") != args.project
            ):
                raise StorageError(
                    "The deployment descriptor must target the selected project."
                )
            if (
                sum(c.get("name") == "web" for c in descriptor["spec"]["components"])
                != 1
            ):
                raise StorageError(
                    "The deployment descriptor must contain exactly one web component."
                )
        desired = json.loads(RESOURCE.read_text())
        if args.quota_bytes is not None:
            desired["quota_bytes"] = args.quota_bytes
        if not 1048576 <= desired["quota_bytes"] <= 1099511627776:
            raise StorageError("--quota-bytes must be between 1 MiB and 1 TiB.")
        version = subprocess.run(
            ["devplat", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if version.returncode or version.stdout.strip() != CLI_VERSION:
            raise StorageError(
                "Install devplat CLI 0.3.0 using scripts/upgrade-devplat.sh."
            )
        result = setup(
            PlatformCLI(args.profile),
            args.project,
            desired,
            apply=args.apply,
            timeout=args.wait_seconds,
        )
        if descriptor is not None:
            web = next(
                c for c in descriptor["spec"]["components"] if c["name"] == "web"
            )
            web["bindings"] = [{"bindingId": result["binding_id"], "envPrefix": ""}]
            args.update_descriptor.write_text(json.dumps(descriptor, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0
    except (StorageError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(
            "Error: "
            + (
                str(error)
                if isinstance(error, StorageError)
                else "Unable to load storage configuration or execute devplat."
            ),
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print(
            "Interrupted. Provisioning continues; inspect storage before rerunning.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
