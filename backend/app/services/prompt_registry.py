from pathlib import Path
import yaml
from app.schemas.cv import JobProfile

REGISTRY=Path(__file__).resolve().parent.parent / "prompts" / "registry.yaml"

def select_prompt(job: JobProfile):
    data=yaml.safe_load(REGISTRY.read_text())
    role=job.role_family if job.role_family in data["roles"] else "general"
    seniority=job.seniority if job.seniority in data["seniority"] else "entry"
    domain=job.domain if job.domain in data["domains"] else "general"
    role_prompt=data["roles"][role]
    seniority_prompt=data["seniority"][seniority]
    domain_prompt=data["domains"][domain]
    key=f"{role}.{seniority}.{domain}"
    return key, "\n\n".join([data["base"],role_prompt,seniority_prompt,domain_prompt])
