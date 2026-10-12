"""Isolated local publication, restart, and actual PostgreSQL backup/restore proof."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import requests
from odip_worker.contract import KIT
from odip_worker.fixtures import operator_session, publish_fixture
from odip_worker.publication import claim_and_validate

ROOT=Path(__file__).resolve().parents[1]

def verify(base_url):
    for name in ("energy-reference-wasserburg-am-inn-2024","non-energy-mobility-counts-2024"):
        expected=(KIT/"fixtures"/name/"manifest.json").read_bytes()
        response=requests.get(base_url+f"/api/v1/datasets/{name}/versions/1.0.0",timeout=15)
        response.raise_for_status()
        assert response.content==expected,"Manifest changed"
        assert response.headers["ETag"]=='"'+hashlib.sha256(expected).hexdigest()+'"'
        conditional=requests.get(response.url,headers={"If-None-Match":response.headers["ETag"]},timeout=15)
        assert conditional.status_code==304
        for artifact in response.json()["artifacts"]:
            downloaded=requests.get(response.url+"/"+artifact["path"],timeout=15)
            downloaded.raise_for_status()
            assert hashlib.sha256(downloaded.content).hexdigest()==artifact["sha256"],"Artifact changed"

def main():
    os.environ["ODIP_IDENTITY_MODE"]="development"
    name="odip-acceptance-"+uuid.uuid4().hex[:12]
    jar=next((ROOT/"services/platform-api/build/libs").glob("*SNAPSHOT.jar"))
    java=None
    subprocess.run(["docker","run","--detach","--rm","--name",name,"--publish","127.0.0.1::5432","--env","POSTGRES_DB=odip_acceptance","--env","POSTGRES_USER=odip","--env","POSTGRES_PASSWORD=odip","postgres:18-alpine"],check=True,stdout=subprocess.DEVNULL)
    with tempfile.TemporaryDirectory(prefix="odip-acceptance-") as temporary:
        log=open(Path(temporary)/"api.log","wb")
        try:
            port=subprocess.check_output(["docker","port",name,"5432/tcp"],text=True).strip().rsplit(":",1)[1]
            for _ in range(100):
                ready=subprocess.run(["docker","exec",name,"pg_isready","-U","odip"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                if ready.returncode==0: break
                time.sleep(.2)
            # Allocate the application port through the OS, separate from production.
            import socket
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0)); http_port=sock.getsockname()[1]
            base_url=f"http://127.0.0.1:{http_port}"
            def start(database):
                nonlocal java
                java=subprocess.Popen(["java","-jar",str(jar),
                    f"--spring.datasource.url=jdbc:postgresql://localhost:{port}/{database}",
                    "--spring.datasource.username=odip","--spring.datasource.password=odip",
                    "--server.address=127.0.0.1",f"--server.port={http_port}",
                    "--odip.authorization.require-principal-context=false","--odip.source-policy.hosts=github.com"],
                    stdout=log,stderr=log)
                for _ in range(240):
                    if java.poll() is not None: raise RuntimeError("Local API exited; inspect startup configuration")
                    try:
                        response=requests.get(base_url+"/actuator/health/readiness",timeout=1)
                        if response.status_code==200: return
                    except requests.ConnectionError: pass
                    time.sleep(.25)
                raise RuntimeError("Local API readiness timed out")
            def stop():
                if java and java.poll() is None:
                    java.terminate()
                    try: java.wait(timeout=15)
                    except subprocess.TimeoutExpired: java.kill(); java.wait()
            start("odip_acceptance")
            session=operator_session(base_url)
            for fixture in ("energy-reference-wasserburg-am-inn-2024","non-energy-mobility-counts-2024"):
                publish_fixture(base_url,KIT/"fixtures"/fixture,session)
                assert claim_and_validate(base_url)
            verify(base_url)
            # A schema-valid missing-hour input must fail the semantic quality policy.
            draft=publish_fixture(base_url,KIT/"fixtures/energy-reference-wasserburg-am-inn-2024",session,version="1.0.1",mutate=lambda data:data["pv-yield"]["values"].pop())
            assert claim_and_validate(base_url)
            failed=session.get(base_url+"/api/v1/publication-drafts/"+draft["id"],timeout=15)
            failed.raise_for_status()
            assert failed.json()["status"]=="FAILED"
            assert requests.get(base_url+"/api/v1/datasets/energy-reference-wasserburg-am-inn-2024/versions/1.0.1",timeout=15).status_code==409
            corrected=publish_fixture(base_url,KIT/"fixtures/energy-reference-wasserburg-am-inn-2024",session,version="1.0.2")
            assert claim_and_validate(base_url)
            assert requests.get(base_url+"/api/v1/datasets/energy-reference-wasserburg-am-inn-2024/versions/1.0.2",timeout=15).status_code==200
            verify(base_url)
            stop(); start("odip_acceptance"); verify(base_url)
            stop()
            backup=Path(temporary)/"publication.dump"
            with backup.open("wb") as destination:
                subprocess.run(["docker","exec",name,"pg_dump","-U","odip","-d","odip_acceptance","-Fc"],check=True,stdout=destination)
            subprocess.run(["docker","exec",name,"createdb","-U","odip","odip_restored"],check=True)
            with backup.open("rb") as source:
                subprocess.run(["docker","exec","-i",name,"pg_restore","-U","odip","-d","odip_restored"],check=True,stdin=source)
            start("odip_restored"); verify(base_url)
            print("PASS: energy and non-energy publication, semantic rejection, version isolation, restart, PostgreSQL backup/restore")
            print("Principal context and dataset grants are verified by API tests; actual platform authentication requires deployed checks.")
        finally:
            if java and java.poll() is None:
                java.terminate()
                try: java.wait(timeout=15)
                except subprocess.TimeoutExpired: java.kill(); java.wait()
            log.close()
            subprocess.run(["docker","stop",name],check=False,stdout=subprocess.DEVNULL)
if __name__=="__main__": main()
