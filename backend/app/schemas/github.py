from pydantic import BaseModel, Field


class GitHubInspectRequest(BaseModel):
    url: str


class GitHubLink(BaseModel):
    label: str
    url: str


class GitHubRepositoryEvidence(BaseModel):
    full_name: str
    name: str
    url: str
    default_branch: str = ""
    description: str = ""
    visibility: str = "public"
    language: str = ""
    languages: dict[str, int] = Field(default_factory=dict)
    topics: list[str] = Field(default_factory=list)
    stars: int = 0
    forks: int = 0
    readme: str = ""
    technologies: list[str] = Field(default_factory=list)
    important_files: list[str] = Field(default_factory=list)
    code_samples: list[dict[str, str]] = Field(default_factory=list)
    evidence_summary: str = ""
