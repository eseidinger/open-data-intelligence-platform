"""Preview or provision the worker service binding for odip, odip-test or odip-test-local.

Apply requests missing service access, approves only ingestion-workers, waits for
activation and saves its non-secret prefix in the selected deployment descriptor.
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "bootstrap_deployment", ROOT / "scripts/bootstrap-deployment.py"
)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
storage = bootstrap.storage


def validate_service(service, project, name):
    values = service.get("spec", {})
    if (
        service.get("project") != project
        or service.get("name") != name
        or values.get("providerProject") != project
        or values.get("application") != project
        or values.get("projectWideCredential") is not True
    ):
        raise storage.StorageError(
            "Worker service access does not target this project and application."
        )
    if service.get("state") not in ("pending", "provisioning", "active"):
        raise storage.StorageError(
            "Worker service access is inactive. Review it in the platform before rerunning."
        )


def configure(
    cli, project, *, apply=False, timeout=120, clock=time.monotonic, sleep=time.sleep
):
    bootstrap.read_descriptor(project)
    context = cli.invoke(["access", "context", "--project", project])
    if (
        context.get("project") != project
        or context.get("application") != project
        or not context.get("eligible")
        or context.get("component") != "web"
        or context.get("permissions", {}).get("manage") is not True
        or context.get("permissions", {}).get("consume") is not True
    ):
        raise storage.StorageError(
            "Deploy web first and use a project administrator with access-management and service-request permissions."
        )
    policy = cli.invoke(
        ["access", "policy", "get", "--project", project, "--application", project]
    )
    if policy.get("state") != "active":
        raise storage.StorageError(
            "Apply configure-access-policy.py and wait for the policy to become active first."
        )
    groups = storage.items(
        cli.invoke(["access", "groups", "list", "--project", project]), "items"
    )
    worker_groups = [g for g in groups if g.get("name") == "ingestion-workers"]
    if (
        len(worker_groups) != 1
        or worker_groups[0].get("state") != "active"
        or not re.fullmatch(r"grp_[0-9a-f]{32}", worker_groups[0].get("id", ""))
    ):
        raise storage.StorageError(
            "Configure one active ingestion-workers group before requesting service access."
        )
    group_id = worker_groups[0]["id"]
    name = project + "-worker"

    def services():
        return storage.items(
            cli.invoke(["access", "services", "list", "--project", project]), "items"
        )

    matches = [
        row
        for row in services()
        if row.get("project") == project and row.get("name") == name
    ]
    if len(matches) > 1:
        raise storage.StorageError(
            "Multiple worker service requests match. Review them before rerunning."
        )
    service = matches[0] if matches else None
    if service:
        validate_service(service, project, name)
        if service["state"] != "pending" and service.get("spec", {}).get("groups") != [
            group_id
        ]:
            raise storage.StorageError(
                "Existing worker access must belong only to ingestion-workers."
            )
    if not apply:
        return {
            "project": project,
            "apply": False,
            "name": name,
            "action": "request-and-approve"
            if service is None
            else "approve"
            if service["state"] == "pending"
            else "reuse",
            "state": service.get("state") if service else None,
            "descriptor": str(bootstrap.descriptor_path(project)),
        }
    if service is None:
        service = cli.invoke(
            [
                "access",
                "services",
                "request",
                "--project",
                project,
                "--project-wide-credential",
                "--file",
                "-",
                "--idempotency-key",
                name,
            ],
            {
                "name": name,
                "providerProject": project,
                "application": project,
                "projectWideCredential": True,
            },
        )
        validate_service(service, project, name)
    service_id = service.get("id")
    if not isinstance(service_id, str) or not re.fullmatch(
        r"svc_[0-9a-f]{32}", service_id
    ):
        raise storage.StorageError("Worker service access has an invalid resource ID.")
    if service["state"] == "pending":
        etag = service.get("etag")
        if not isinstance(etag, str) or not re.fullmatch(r'"[1-9][0-9]*"', etag):
            raise storage.StorageError(
                "Worker access has no valid ETag; refusing unguarded approval."
            )
        cli.invoke(
            [
                "access",
                "services",
                "approve",
                service_id,
                "--project",
                project,
                "--group",
                group_id,
                "--if-match",
                etag,
                "--wait",
                "--timeout",
                str(timeout),
            ],
            timeout=timeout + 45,
        )
    deadline = clock() + timeout
    while True:
        observed = [row for row in services() if row.get("id") == service_id]
        if len(observed) != 1:
            raise storage.StorageError(
                "Worker service access disappeared while waiting."
            )
        service = observed[0]
        validate_service(service, project, name)
        if service["state"] == "active":
            break
        if service["state"] != "provisioning" or clock() >= deadline:
            raise storage.StorageError(
                "Worker access did not activate. Inspect access operations before rerunning."
            )
        sleep(min(2, max(0, deadline - clock())))
    prefix = service["spec"].get("secretPrefix", "")
    if service["spec"].get("groups") != [group_id] or not re.fullmatch(
        r"ACCESS_[A-Z0-9_]+", prefix
    ):
        raise storage.StorageError(
            "Active worker access has an unexpected group or managed prefix."
        )
    for other in bootstrap.DESCRIPTORS:
        if other == project:
            continue
        other_prefix = bootstrap.read_descriptor(other)["spec"]["configuration"][
            "values"
        ].get("ODIP_WORKER_BINDING_PREFIX")
        if prefix == other_prefix:
            raise storage.StorageError(
                "Worker identities for different environments must use different managed prefixes."
            )
    path = bootstrap.descriptor_path(project)
    # Reload so configuration edits made during activation are preserved.
    application = bootstrap.read_descriptor(project)
    application["spec"]["configuration"]["values"]["ODIP_WORKER_BINDING_PREFIX"] = (
        prefix
    )
    path.write_text(json.dumps(application, indent=2) + "\n")
    return {
        "project": project,
        "state": "active",
        "service_id": service_id,
        "principal_id": service["spec"].get("principalId"),
        "worker_binding_prefix": prefix,
        "descriptor": str(path),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", required=True, choices=tuple(bootstrap.DESCRIPTORS)
    )
    parser.add_argument("--profile")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Request/approve worker access and save its prefix; otherwise preview",
    )
    parser.add_argument("--wait-seconds", type=int, default=120)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.wait_seconds <= 600:
            raise storage.StorageError("--wait-seconds must be between 1 and 600.")
        bootstrap.check_cli()
        result = configure(
            storage.PlatformCLI(args.profile),
            args.project,
            apply=args.apply,
            timeout=args.wait_seconds,
        )
        print(json.dumps(result, indent=2))
        return 0
    except (
        storage.StorageError,
        OSError,
        ValueError,
        KeyError,
        subprocess.TimeoutExpired,
    ) as error:
        message = (
            str(error)
            if isinstance(error, storage.StorageError)
            else "Unable to configure worker access. Inspect the platform before rerunning."
        )
        print("Error: " + message, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Interrupted. Submitted operations continue; inspect worker access before rerunning.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
