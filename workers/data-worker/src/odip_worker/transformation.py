"""Dispatch only adapters declared by the installed worker package."""
import importlib
import json
from importlib.resources import files

ADAPTERS=json.loads(files("odip_worker").joinpath("adapters.json").read_text())

def transform(payload, selector):
    if selector is None: return None
    adapter=ADAPTERS.get(selector)
    if adapter is None: raise ValueError("Unsupported transformation selector")
    module, function=adapter["handler"].split(":")
    data=getattr(importlib.import_module(module),function)(payload)
    return {"id":adapter["id"],"data":data}
