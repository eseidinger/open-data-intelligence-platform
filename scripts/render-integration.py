"""Pin deployment images and managed binding; never applies external changes."""
import argparse
import copy
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate_host(host):
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if (
        not host
        or len(host) > 253
        or not re.fullmatch(label + r"(?:\." + label + r")+", host)
        or host.endswith(".invalid")
    ):
        raise ValueError("Supply installation-owned DNS hostnames in the deployment descriptor")


def render(image_tag, prefix=None, *, application=None):
    if not re.fullmatch(r"[0-9a-f]{40}", image_tag):
        raise ValueError("Use the immutable 40-character commit image tag")
    application = (
        copy.deepcopy(application)
        if application is not None
        else json.loads((ROOT / "application.json").read_text())
    )
    values = application["spec"]["configuration"]["values"]
    if prefix is None:
        prefix = values.get("ODIP_WORKER_BINDING_PREFIX", "")
    if not isinstance(prefix, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", prefix) or prefix == "RENDER_REQUIRED":
        raise ValueError("Set ODIP_WORKER_BINDING_PREFIX in the descriptor or use --worker-secret-prefix with the approved binding's secretPrefix")
    origin = urlsplit(values.get("ODIP_API_URL", ""))
    if (
        origin.scheme != "https"
        or origin.username is not None
        or origin.password is not None
        or origin.port not in (None, 443)
        or origin.path not in ("", "/")
        or origin.query
        or origin.fragment
    ):
        raise ValueError("ODIP_API_URL in the deployment descriptor must be a public HTTPS origin on port 443")
    validate_host(origin.hostname)
    components = {component["name"]: component for component in application["spec"]["components"]}
    if not {"web", "ingestion-worker"}.issubset(components):
        raise ValueError("The deployment descriptor must include web and ingestion-worker components")
    outbound = components["ingestion-worker"].get("outbound", [])
    for rule in outbound:
        if "dns" in rule:
            validate_host(rule["dns"])
    if not any(rule.get("dns") == origin.hostname and rule.get("port") == 443 for rule in outbound):
        raise ValueError("Declare ingestion-worker HTTPS egress to the ODIP_API_URL host in the deployment descriptor")
    components["web"]["runtime"]["image"] = "docker.io/eseidinger/odip-platform:" + image_tag
    components["ingestion-worker"]["runtime"]["image"] = "docker.io/eseidinger/odip-data-worker:" + image_tag
    values["ODIP_WORKER_BINDING_PREFIX"] = prefix
    return application


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-tag", required=True)
    parser.add_argument("--worker-secret-prefix", help="Override the descriptor's approved worker binding prefix")
    parser.add_argument("--file", type=Path, default=ROOT / "application.json", help="Installation deployment descriptor")
    args = parser.parse_args()
    try:
        application = json.loads(args.file.read_text())
        declaration = render(args.image_tag, args.worker_secret_prefix, application=application)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(declaration, indent=2))

if __name__ == "__main__":
    main()
