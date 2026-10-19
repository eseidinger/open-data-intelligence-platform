"""Fill production image version placeholders and write deployment JSON to stdout."""
import argparse
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = "__VERSION__"


def render(application, version):
    version = version.removeprefix("v")
    number = r"(?:0|[1-9][0-9]*)"
    prerelease = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    if (len(version) > 128 or not re.fullmatch(
            rf"{number}\.{number}\.{number}(?:-{prerelease}(?:\.{prerelease})*)?", version)):
        raise ValueError("Use a release version such as 0.4.1 or v0.4.1 (optional prerelease; no build metadata)")
    result = copy.deepcopy(application)
    if result.get("metadata", {}).get("name") != "odip" or result["metadata"].get("project") != "odip":
        raise ValueError("The release descriptor must target project odip")
    components = result["spec"]["components"]
    if {c["name"] for c in components} != {"web", "ingestion-worker"} or len(components) != 2:
        raise ValueError("The release descriptor must contain web and ingestion-worker")
    for component in components:
        image = component["runtime"]["image"]
        if not image.endswith(":" + PLACEHOLDER):
            raise ValueError(f"Component {component['name']} image must end with :{PLACEHOLDER}")
        component["runtime"]["image"] = image.removesuffix(PLACEHOLDER) + version
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version or Git tag, e.g. 0.4.1 or v0.4.1")
    parser.add_argument("--file", type=Path, default=ROOT / "infrastructure/deployments/application.json")
    args = parser.parse_args()
    try:
        declaration = render(json.loads(args.file.read_text()), args.version)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(declaration, indent=2))


if __name__ == "__main__":
    main()
