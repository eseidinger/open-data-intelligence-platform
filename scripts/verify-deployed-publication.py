"""Read-only acceptance checks using an already approved reader binding."""
import argparse
import hashlib
import os
import requests
from odip_worker.auth import api_url, call
from odip_worker.contract import KIT
from odip_worker.energy.profile import validate_profile

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--api-url",required=True)
    parser.add_argument("--binding-prefix",required=True)
    args=parser.parse_args()
    os.environ["ODIP_IDENTITY_MODE"]="platform"
    os.environ["ODIP_WORKER_BINDING_PREFIX"]=args.binding_prefix
    origin=api_url(args.api_url)
    name="energy-reference-wasserburg-am-inn-2024"
    path=f"/api/v1/datasets/{name}/versions/1.0.0"
    for supplied in [{},{"X-Platform-Principal-Id":"prn_forged","X-Platform-Principal-Kind":"service","X-Platform-Principal-Issuer":"https://forged.test","X-Platform-Principal-Subject":"forged","X-Platform-Principal-Client-Id":"forged","X-Platform-Principal-Group-Ids":"grp_forged"}]:
        response=requests.get(origin+path,headers=supplied,allow_redirects=False,timeout=20)
        assert response.status_code==401,"Unauthenticated or spoofed identity reached the protected route"
    response=call("get",origin+path)
    response.raise_for_status()
    manifest=response.json()
    expected=(KIT/"fixtures"/name/"manifest.json").read_bytes()
    assert response.content==expected,"Manifest differs from the pinned reference fixture"
    etag='"'+hashlib.sha256(expected).hexdigest()+'"'
    assert response.headers["ETag"]==etag
    # call supplies credentials internally; conditional headers must be explicit.
    from odip_worker.auth import headers
    conditional=requests.get(origin+path,headers={**headers(),"If-None-Match":etag},allow_redirects=False,timeout=20)
    assert conditional.status_code==304
    artifacts={}
    for descriptor in manifest["artifacts"]:
        assert descriptor["path"]=="artifacts/"+descriptor["artifactId"]
        artifact=call("get",origin+path+"/"+descriptor["path"])
        artifact.raise_for_status()
        assert hashlib.sha256(artifact.content).hexdigest()==descriptor["sha256"]
        artifacts[descriptor["artifactId"]]=artifact.json()
    validate_profile(manifest,artifacts)
    foreign=call("get",origin+"/api/v1/datasets/non-energy-mobility-counts-2024/versions/1.0.0")
    assert foreign.status_code==403,"Reader must be scoped only to the energy dataset"
    denied=call("post",origin+"/api/v1/datasets",json={})
    assert denied.status_code in (401,403),"Reader cannot write"
    print("PASS: authenticated fixture retrieval, conditional reads, spoof rejection, dataset scope, and write denial")
    print("Rotation, unrelated egress denial, platform outage, and deployed backup/restore require the installation's operational acceptance run.")
if __name__=="__main__": main()
