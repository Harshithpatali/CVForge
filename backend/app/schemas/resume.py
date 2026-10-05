from pydantic import BaseModel, Field


class ResumeLink(BaseModel):
    label: str
    url: str


class ResumeExperience(BaseModel):
    company: str
    title: str
    dates: str
    location: str = ""
    bullets: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    institution: str
    degree: str
    field: str = ""
    dates: str = ""


class ResumeProject(BaseModel):
    name: str
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    url: str = ""
    links: list[ResumeLink] = Field(default_factory=list)


class GeneratedResume(BaseModel):
    name: str
    contact_line: str
    headline: str
    summary: str
    skills: list[str]
    skill_groups: dict[str, list[str]] = Field(default_factory=dict)
    professional_links: list[ResumeLink] = Field(default_factory=list)
    experience: list[ResumeExperience]
    projects: list[ResumeProject]
    education: list[ResumeEducation]
    certifications: list[str] = Field(default_factory=list)
