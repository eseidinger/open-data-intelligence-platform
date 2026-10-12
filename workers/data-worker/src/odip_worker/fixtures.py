"""Publish reference inputs through operator routes, then validate through worker routes."""
import argparse
import base64
import hashlib
import json
import os
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlsplit
import requests
from odip_worker.auth import api_url
from odip_worker.contract import KIT, canonical_bytes, load_json
from odip_worker.energy.profile import reference_outputs
from odip_worker.publication import claim_and_validate

def operator_session(base_url):
    session = requests.Session()
    if os.environ.get("ODIP_IDENTITY_MODE") == "development":
        session.headers.update({
            "X-Platform-Principal-Id":"development-operator","X-Platform-Principal-Kind":"user",
            "X-Platform-Principal-Issuer":"https://odip.internal","X-Platform-Principal-Subject":"development-operator",
            "X-Platform-Principal-Group-Ids":os.getenv("ODIP_GROUP_IDS_USERS","grp_e2987e192a0a41b4a0273c71c14fef47"),
        })
    else:
        cookies = MozillaCookieJar(os.environ["ODIP_OPERATOR_COOKIE_FILE"])
        cookies.load(ignore_discard=True)
        session.cookies = cookies
        csrf = next((c.value for c in cookies if c.name == "__Host-platform-csrf" and c.domain.lstrip(".") == urlsplit(base_url).hostname),None)
        if not csrf: raise ValueError("An authenticated operator CSRF cookie is required")
        session.headers.update({"Origin":base_url,"X-Platform-CSRF-Token":csrf})
    return session

def operation(session, base_url, method, path, **kwargs):
    response = session.request(method,base_url+path,timeout=(10,60),allow_redirects=False,**kwargs)
    if not 200 <= response.status_code < 300: raise RuntimeError(f"Operator request failed with HTTP {response.status_code}")
    return response.json() if response.content else None

def publish_fixture(base_url, folder, session, *, version=None, mutate=None):
    manifest = load_json(folder/"manifest.json")
    if version: manifest["version"] = version
    if manifest["schemaRef"] == "urn:portfolio:energy-configuration-input:v1":
        source = load_json(folder/"source/pvgis-era5-wasserburg-2023.json")
        artifacts = reference_outputs(source)
        raw = (folder/"source/pvgis-era5-wasserburg-2023.json").read_bytes()
    else:
        artifacts = {d["artifactId"]:load_json(folder/"artifacts"/(d["artifactId"]+".json")) for d in manifest["artifacts"]}
        raw = canonical_bytes(next(iter(artifacts.values())))
    if mutate: mutate(artifacts)
    for d in manifest["artifacts"]: d["sha256"] = hashlib.sha256(canonical_bytes(artifacts[d["artifactId"]])).hexdigest()
    registered = operation(session,base_url,"GET","/api/datasets")
    existing = next((d for d in registered if d["name"] == manifest["datasetId"]),None)
    if existing:
        dataset_id = existing["id"]
        source_id = existing["sources"][0]["id"]
    else:
        attribution = manifest["provenance"][0]
        source = operation(session,base_url,"POST","/api/data-sources",json={
            "name":manifest["datasetId"],"sourceType":"API",
            "location":"https://github.com/eseidinger/energy-system-configuration/releases/tag/contract-kit-v0.4.0",
            "owner":attribution["sourceOwner"],"license":attribution["license"],
        })
        source_id=source["id"]
        dataset_id=operation(session,base_url,"POST","/api/datasets",json={"name":manifest["datasetId"],"classification":"PUBLIC","sourceIds":[source_id]})["id"]
    # Reuse the same immutable inputs when retrying an existing publication.
    drafts=operation(session,base_url,"GET","/api/v1/publication-drafts")
    existing_draft=next((d for d in drafts if d["manifest"]["datasetId"]==manifest["datasetId"] and d["manifest"]["version"]==manifest["version"]),None)
    if existing_draft:
        if canonical_bytes(existing_draft["manifest"]) != canonical_bytes(manifest): raise ValueError("Publication version already identifies different bytes")
        draft=existing_draft
    else:
        captured=operation(session,base_url,"POST","/api/v1/reference-inputs",json={"sourceId":source_id,"input":{
            "payload":base64.b64encode(raw).decode(),"contentLength":len(raw),"contentType":"application/json",
            "checksumSha256":hashlib.sha256(raw).hexdigest(),"sourceVersion":"contract-kit/0.4.0",
            "validation":{"status":"VALID","detectedFormat":"JSON","recordCount":1},
        }})
        draft=operation(session,base_url,"POST","/api/v1/publication-drafts",headers={"Idempotency-Key":manifest["datasetId"]+"/"+manifest["version"]},json={"datasetId":dataset_id,"manifest":manifest,"rawArtifactIds":[captured["rawArtifactId"]]})
    if draft["status"]=="DRAFT":
        for descriptor in manifest["artifacts"]:
            operation(session,base_url,"PUT",f'/api/v1/publication-drafts/{draft["id"]}/artifacts/{descriptor["artifactId"]}',headers={"Content-Type":"application/octet-stream"},data=canonical_bytes(artifacts[descriptor["artifactId"]]))
        operation(session,base_url,"POST",f'/api/v1/publication-drafts/{draft["id"]}/publish',headers={"Idempotency-Key":"publish/"+draft["id"]})
    return draft

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--api-url",default=os.getenv("ODIP_API_URL"))
    parser.add_argument("--fixture",choices=["energy","non-energy","all"],default="all")
    parser.add_argument("--validate",action="store_true",help="Also consume jobs using the worker binding")
    args=parser.parse_args()
    base_url=api_url(args.api_url)
    session=operator_session(base_url)
    names={"energy":"energy-reference-wasserburg-am-inn-2024","non-energy":"non-energy-mobility-counts-2024"}
    for key,name in names.items():
        if args.fixture in (key,"all"):
            draft=publish_fixture(base_url,KIT/"fixtures"/name,session)
            if args.validate: claim_and_validate(base_url)
            print(json.dumps({"datasetId":name,"version":"1.0.0","draftId":draft["id"],"manifestSha256":draft["manifestSha256"]}))
if __name__=="__main__": main()
