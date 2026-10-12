"""Legacy annual observation adapter."""
import json

def normalize_payload(payload):
    dataset=json.loads(payload)
    dimensions=dataset["dimension"]
    value=next(iter(dataset["value"].values()))
    return {
        "indicatorCode":"RENEWABLE_ENERGY_SHARE",
        "geoCode":_single_category(dimensions,"geo"),
        "observationYear":int(_single_category(dimensions,"time")),
        "unitCode":_single_category(dimensions,"unit"),
        "observationValue":value,
    }

def _single_category(dimensions,name):
    categories=dimensions[name]["category"]["index"]
    if len(categories)!=1: raise ValueError(f"Expected one {name} category")
    return next(iter(categories))
