from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional

class Contact(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""

class Experience(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)

class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""

class ProjectLink(BaseModel):
    label: str
    url: str


class Project(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    url: str = ""
    links: list[ProjectLink] = Field(default_factory=list)

class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    contact: Contact = Field(default_factory=Contact)
    headline: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    raw_text: str = ""
    source_format: str = ""

class JobProfile(BaseModel):
    title: str = ""
    company: str = ""
    role_family: str = "general"
    seniority: str = "entry"
    domain: str = "general"
    location: str = ""
    employment_type: str = ""
    must_have_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    raw_text: str = ""

class QuestionnaireItem(BaseModel):
    key: str
    question: str
    reason: str
    required: bool = True

class GenerateRequest(BaseModel):
    job: JobProfile
    candidate: CandidateProfile
    answers: dict[str, str] = Field(default_factory=dict)
    template: str = "auto"

class GenerateResponse(BaseModel):
    job_id: int
    resume_id: int
    prompt_key: str
    ats_score: float
    warnings: list[str]
    resume: dict
