import io, re
from pathlib import Path
from pypdf import PdfReader
from docx import Document

SECTION_ALIASES = {
    "summary": ["summary", "professional summary", "profile", "objective"],
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "education": ["education", "academic background"],
    "skills": ["skills", "technical skills", "core skills", "competencies"],
    "projects": ["projects", "selected projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses"],
    "awards": ["awards", "honors"],
}

def extract_text(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    if ext in {".txt", ".md"}:
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, or MD.")

def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "")
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in text.splitlines()]
    return "\n".join(x for x in lines if x)

def split_sections(text: str) -> dict[str, str]:
    lines = clean_text(text).splitlines()
    sections = {k: [] for k in SECTION_ALIASES}
    current = None
    for line in lines:
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        matched = next((k for k, aliases in SECTION_ALIASES.items() if normalized in aliases), None)
        if matched:
            current = matched
            continue
        if current:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}

def parse_bullets(section: str) -> list[str]:
    if not section: return []
    out=[]
    for line in section.splitlines():
        line=re.sub(r"^[•●▪◦*\-]+\s*", "", line).strip()
        if line: out.append(line)
    return out

def parse_candidate(text: str, filename: str):
    from app.schemas.cv import CandidateProfile, Contact, Experience, Education, Project
    clean=clean_text(text); sec=split_sections(clean)
    lines=clean.splitlines()
    name=lines[0] if lines else ""
    emails=re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", clean)
    urls=re.findall(r"https?://\S+|www\.\S+", clean)
    linkedin=next((u.rstrip(".,)") for u in urls if "linkedin" in u.lower()), "")
    github=next((u.rstrip(".,)") for u in urls if "github" in u.lower()), "")
    phone=next((re.sub(r"\s+", " ", m).strip() for m in re.findall(r"(?:\+?\d[\d ()-]{8,}\d)", clean)), "")
    skills=[]
    for x in re.split(r"[,|•;\n]", sec["skills"]):
        x=x.strip(" -")
        if x and len(x)<80: skills.append(x)
    # Preserve the original experience/project blocks; later human/LLM review can normalize them.
    exp=Experience(bullets=parse_bullets(sec["experience"])) if sec["experience"] else None
    proj=Project(name="Projects", bullets=parse_bullets(sec["projects"])) if sec["projects"] else None
    edu=Education() if not sec["education"] else Education(institution=parse_bullets(sec["education"])[0] if parse_bullets(sec["education"]) else "")
    return CandidateProfile(
        contact=Contact(name=name,email=emails[0] if emails else "",phone=phone,linkedin=linkedin,github=github),
        summary=sec["summary"], skills=skills, experience=[exp] if exp else [],
        projects=[proj] if proj else [], education=[edu] if edu.institution else [],
        certifications=parse_bullets(sec["certifications"]), awards=parse_bullets(sec["awards"]),
        raw_text=clean, source_format=Path(filename).suffix.lower().lstrip("."))
