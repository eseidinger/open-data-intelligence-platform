"""Preview or deploy web alone while bootstrapping odip, odip-test or odip-test-local.

The saved descriptor is never changed. Apply refuses to remove an already
declared ingestion worker; use the normal deployment workflow after bootstrap.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


storage = load_script("setup-storage")
release = load_script("render-release")


DESCRIPTORS = {
    "odip": "application.json",
    "odip-test": "application-test.json",
    "odip-test-local": "application-test-local.json",
}


def descriptor_path(project):
    if project not in DESCRIPTORS:
        raise storage.StorageError("Select project " + ", ".join(DESCRIPTORS) + ".")
    return ROOT / "infrastructure/deployments" / DESCRIPTORS[project]


def read_descriptor(project):
    application = json.loads(descriptor_path(project).read_text())
    if application.get("metadata", {}).get("name") != project or application["metadata"].get("project") != project:
        raise storage.StorageError("The deployment descriptor must target the selected project.")
    return application


def check_cli():
    result = subprocess.run(["devplat", "--version"], capture_output=True, text=True, timeout=15, check=False)
    if result.returncode or result.stdout.strip() != storage.CLI_VERSION:
        raise storage.StorageError("Install devplat 0.3.0 using scripts/upgrade-devplat.sh.")


def declaration(project, version=None):
    application = read_descriptor(project)
    if project == "odip":
        if not version:
            raise storage.StorageError("Production bootstrap requires --version for an already published release.")
        application = release.render(application, version)
    elif version:
        raise storage.StorageError(f"{project} uses latest images; omit --version.")
    elif any(not c["runtime"]["image"].endswith(":latest") for c in application["spec"]["components"]):
        raise storage.StorageError("The test descriptor must use latest images.")
    web = [c for c in application["spec"]["components"] if c.get("name") == "web" and c.get("type") == "service" and c.get("exposure") == "public"]
    if len(web) != 1:
        raise storage.StorageError("The descriptor must declare one public web service.")
    bindings = web[0].get("bindings", [])
    if len(bindings) != 1 or bindings[0].get("envPrefix", "") != "":
        raise storage.StorageError("Run setup-storage.py --apply --update-descriptor for this project first.")
    storage.identity({"binding_id": bindings[0].get("bindingId")}, "binding_id")
    application["spec"]["components"] = web
    application["spec"]["configuration"]["values"].pop("ODIP_WORKER_BINDING_PREFIX", None)
    return application


def deploy(cli, project, application, timeout):
    projects = cli.invoke(["projects", "list"], allow_list=True)
    if not isinstance(projects, list) or any(not isinstance(p, dict) for p in projects):
        raise storage.StorageError("The CLI returned an invalid project list.")
    matches = [p for p in projects if p.get("name") == project]
    if len(matches) != 1 or matches[0].get("status") in ("retired", "retiring", "purging", "purged"):
        raise storage.StorageError("Create an active project before bootstrapping.")
    if any(c.get("name") == "ingestion-worker" for c in (matches[0].get("spec") or {}).get("components", [])):
        raise storage.StorageError("The project already declares ingestion-worker. Bootstrap would remove it; use normal deployment instead.")
    return cli.invoke(["deploy", "apply", "--project", project, "--file", "-", "--wait", "--timeout", str(timeout)],
                      application, timeout=timeout + 45)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, choices=tuple(DESCRIPTORS))
    parser.add_argument("--profile")
    parser.add_argument("--version", help="Already published production release, e.g. v0.4.1")
    parser.add_argument("--apply", action="store_true", help="Deploy web and wait for readiness; otherwise print the declaration")
    parser.add_argument("--wait-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.wait_seconds <= 600:
            raise storage.StorageError("--wait-seconds must be between 1 and 600.")
        application = declaration(args.project, args.version)
        if args.apply:
            check_cli()
            result = deploy(storage.PlatformCLI(args.profile), args.project, application, args.wait_seconds)
        else:
            result = application
        print(json.dumps(result, indent=2))
        return 0
    except (storage.StorageError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        message = str(error) if isinstance(error, (storage.StorageError, ValueError)) else "Unable to complete bootstrap. Inspect submitted operations before rerunning."
        print("Error: " + message, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Submitted deployment continues; inspect it before rerunning.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
