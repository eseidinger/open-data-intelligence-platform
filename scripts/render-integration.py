"""Render deployment and disjoint access policy; never applies external changes."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def render(image_tag, odip_host, identity_host, prefix):
    if not re.fullmatch(r"[0-9a-f]{40}",image_tag): raise ValueError("Use the immutable 40-character commit image tag")
    for host in (odip_host,identity_host):
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?",host) or host.endswith(".invalid"): raise ValueError("Supply installation-owned DNS hostnames")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*",prefix): raise ValueError("Invalid managed binding prefix")
    application = json.loads((ROOT/"application.json").read_text())
    for component in application["spec"]["components"]:
        if component["name"] == "web":
            component["runtime"]["image"] = "docker.io/eseidinger/odip-platform:" + image_tag
        else:
            component["runtime"]["image"] = "docker.io/eseidinger/odip-data-worker:" + image_tag
            component["outbound"] = [{"dns":host,"port":443} for host in sorted({odip_host,identity_host,"re.jrc.ec.europa.eu","ec.europa.eu","jsonplaceholder.typicode.com"})]
    application["spec"]["configuration"]["values"].update({
        "ODIP_API_URL":"https://"+odip_host,"ODIP_IDENTITY_MODE":"platform",
        "ODIP_WORKER_BINDING_PREFIX":prefix,
        "ODIP_SOURCE_HOSTS":"jsonplaceholder.typicode.com,ec.europa.eu,re.jrc.ec.europa.eu,github.com",
    })
    return application

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image-tag",required=True)
    parser.add_argument("--odip-host",required=True)
    parser.add_argument("--identity-host",required=True)
    parser.add_argument("--worker-secret-prefix",required=True)
    args=parser.parse_args()
    print(json.dumps(render(args.image_tag,args.odip_host,args.identity_host,args.worker_secret_prefix),indent=2))

if __name__=="__main__": main()
