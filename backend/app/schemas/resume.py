from pydantic import BaseModel, Field

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

class GeneratedResume(BaseModel):
    name: str
    contact_line: str
    headline: str
    summary: str
    skills: list[str]
    experience: list[ResumeExperience]
    projects: list[ResumeProject]
    education: list[ResumeEducation]
    certifications: list[str] = Field(default_factory=list)
