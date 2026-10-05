from pathlib import Path
import yaml

REGISTRY=Path(__file__).resolve().parent.parent / "templates" / "registry.yaml"

def select_template(role_family: str, requested: str = "auto"):
    data=yaml.safe_load(REGISTRY.read_text())["templates"]
    if requested != "auto" and requested in data:
        return requested, data[requested]
    for key, meta in data.items():
        if role_family in meta.get("roles", []):
            return key, meta
    return "classic_ats", data["classic_ats"]
