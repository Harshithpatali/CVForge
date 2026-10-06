import io
import re
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

from app.schemas.cv import CandidateProfile, Contact, Education, Experience, Project, ProjectLink


SECTION_ALIASES = {
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "objective",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "professional employment",
    ],
    "education": [
        "education",
        "academic background",
    ],
    "skills": [
        "skills",
        "technical skills",
        "technical skill",
        "core skills",
        "competencies",
    ],
    "projects": [
        "projects",
        "selected projects",
        "selected data science projects",
        "academic projects",
        "data science projects",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
    ],
    "awards": [
        "awards",
        "honors",
    ],
}

BULLET_RE = re.compile(r"^[•●▪◦*\-–—]\s*")
URL_RE = re.compile(r"https?://[^\s|<>}\]]+|www\.[^\s|<>}\]]+", re.I)
LATEX_HREF_RE = re.compile(r"\\(?:href|hrefurl)\s*\{([^{}]+)\}\s*\{([^{}]*)\}", re.I)
LATEX_URL_RE = re.compile(r"\\url\s*\{([^{}]+)\}", re.I)
LATEX_SECTION_RE = re.compile(
    r"\\(?:section|subsection|subsubsection|paragraph)\*?\s*\{([^{}]+)\}",
    re.I,
)
LATEX_TEXTBF_RE = re.compile(r"\\textbf\s*\{([^{}]+)\}", re.I)
LATEX_EMPH_RE = re.compile(r"\\(?:emph|textit)\s*\{([^{}]+)\}", re.I)


def _normalise_url(url: str) -> str:
    url = re.sub(r"[),.;:]+$", "", str(url or "").strip())
    if url.startswith("www."):
        return "https://" + url
    return url


def _clean_latex_markup(value: str) -> str:
    text = str(value or "")
    # Resolve the most useful structural commands first.
    text = re.sub(r"\\(?:href|hrefurl)\s*\{([^{}]+)\}\s*\{([^{}]*)\}", r"\2", text)
    text = re.sub(r"\\url\s*\{([^{}]+)\}", r"\1", text)
    text = LATEX_SECTION_RE.sub(r"\1", text)
    text = LATEX_TEXTBF_RE.sub(r"\1", text)
    text = LATEX_EMPH_RE.sub(r"\1", text)
    text = re.sub(r"\\(?:textcolor|underline)\s*\{[^{}]*\}\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:item|newline|linebreak)\b", "\n", text)
    text = text.replace("~", " ")
    text = re.sub(r"(?<!\\)%.*$", "", text)
    # Remove common TeX-only commands while preserving their arguments.
    text = re.sub(r"\\[a-zA-Z@]+\*?\s*", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _pdf_page_links(page: Any) -> list[str]:
    urls: list[str] = []
    annotations = page.get("/Annots") or []
    for annotation_ref in annotations:
        try:
            annotation = annotation_ref.get_object()
            action = annotation.get("/A")
            if not action:
                continue
            uri = action.get("/URI")
            if uri:
                urls.append(_normalise_url(str(uri)))
        except Exception:
            continue
    return urls


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        links = _pdf_page_links(page)
        if links:
            page_text += "\n" + "\n".join(links)
        pages.append(page_text)
    return "\n".join(pages)


def extract_text(data: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(data)
    if ext == ".docx":
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    if ext in {".txt", ".md", ".tex"}:
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, MD, or TEX.")


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "")
    text = _clean_latex_markup(text)
    lines = [re.sub(r"[ \t]+", " ", x).strip() for x in text.splitlines()]
    return "\n".join(x for x in lines if x)


def split_sections(text: str) -> dict[str, str]:
    lines = clean_text(text).splitlines()
    sections = {key: [] for key in SECTION_ALIASES}
    current: str | None = None

    for line in lines:
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        matched = next(
            (
                key
                for key, aliases in SECTION_ALIASES.items()
                if normalized in {re.sub(r"[^a-z ]", "", alias).strip() for alias in aliases}
            ),
            None,
        )
        if matched:
            current = matched
            continue

        if current:
            sections[current].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def parse_bullets(section: str) -> list[str]:
    if not section:
        return []

    out: list[str] = []
    for line in section.splitlines():
        line = BULLET_RE.sub("", line).strip()
        if line:
            out.append(line)
    return out


def _extract_links(text: str) -> list[ProjectLink]:
    links: list[ProjectLink] = []
    seen: set[str] = set()

    def add(label: str, url: str) -> None:
        clean = _normalise_url(url)
        if not clean or clean in seen:
            return
        seen.add(clean)
        links.append(ProjectLink(label=label, url=clean))

    for match in LATEX_HREF_RE.finditer(text):
        url, label = match.group(1), _clean_latex_markup(match.group(2))
        lower = url.lower()
        if "github" in lower:
            add("GitHub", url)
        elif any(token in lower for token in ("demo", "streamlit", "vercel", "render", "app")):
            add("Live Demo", url)
        else:
            add(label or "Project", url)

    for match in LATEX_URL_RE.finditer(text):
        url = match.group(1)
        lower = url.lower()
        add(
            "GitHub" if "github" in lower else (
                "Live Demo" if any(token in lower for token in ("demo", "streamlit", "vercel", "render", "app"))
                else "Project"
            ),
            url,
        )

    for url in URL_RE.findall(text):
        lower = url.lower()
        add(
            "GitHub" if "github" in lower else (
                "LinkedIn" if "linkedin" in lower else (
                    "Portfolio" if "portfolio" in lower else "Project"
                )
            ),
            url,
        )

    return links


def _section_entry_lines(section: str) -> list[list[str]]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    groups: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        is_bullet = bool(BULLET_RE.match(line))
        if not is_bullet and current:
            groups.append(current)
            current = []
        current.append(line)

    if current:
        groups.append(current)

    return groups


def _project_name_and_metadata(header: str) -> tuple[str, list[str], list[ProjectLink]]:
    clean = _clean_latex_markup(header)
    links = _extract_links(header)
    clean = URL_RE.sub("", clean)

    # Remove common link labels that become visible text in PDF extraction.
    clean = re.sub(
        r"\b(?:GitHub|Live Demo|Demo|Dashboard|Portfolio|Project)\b",
        "",
        clean,
        flags=re.I,
    )

    technologies: list[str] = []
    tech_match = re.search(r"(?:\||-)?\s*([A-Za-z0-9+#. ]+(?:\s*[/,]\s*[A-Za-z0-9+#.& -]+)+)$", clean)
    if tech_match:
        tech_text = tech_match.group(1)
        technologies = [
            item.strip()
            for item in re.split(r"[/|,]", tech_text)
            if item.strip()
        ]
        clean = clean[: tech_match.start()].strip(" |-/")

    clean = re.sub(r"\s{2,}", " ", clean).strip(" |:-")
    return clean or "Project", technologies, links


def _parse_projects(section: str, all_text: str) -> list[Project]:
    if not section:
        return []

    groups = _section_entry_lines(section)
    projects: list[Project] = []

    for group in groups:
        header = group[0]
        body_lines = group[1:]

        # A project can be represented as a LaTeX 	extbf/emph heading,
        # a plain PDF heading, or a heading followed by GitHub/Live Demo.
        name, technologies, links = _project_name_and_metadata(header)

        bullets: list[str] = []
        for line in body_lines:
            clean = BULLET_RE.sub("", line).strip()
            if clean:
                bullets.append(clean)

        if name.lower() in {"projects", "selected projects"}:
            continue

        # Avoid creating a fake project from a section-level prose sentence.
        if not bullets and not links and len(name.split()) < 2:
            continue

        projects.append(
            Project(
                name=name,
                technologies=technologies,
                bullets=bullets,
                links=links,
                url=links[0].url if links else "",
            )
        )

    # If grouped extraction failed, fall back to one project per explicit
    # LaTeX bold/emphasis project heading.
    if not projects:
        candidates = LATEX_TEXTBF_RE.findall(all_text) + LATEX_EMPH_RE.findall(all_text)
        for raw_name in candidates:
            name = _clean_latex_markup(raw_name)
            if name.lower() in SECTION_ALIASES.get("projects", []):
                continue
            projects.append(Project(name=name))

    return projects[:10]


def parse_candidate(text: str, filename: str) -> CandidateProfile:
    clean = clean_text(text)
    sec = split_sections(clean)
    lines = clean.splitlines()

    # Name: first strong non-contact line.
    name = ""
    for line in lines[:10]:
        if "@" not in line and not URL_RE.search(line) and not re.search(r"\d{6,}", line):
            if len(line.split()) <= 8:
                name = line
                break
    if not name and lines:
        name = lines[0]

    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", clean)
    all_links = _extract_links(text)

    linkedin = next((link.url for link in all_links if link.label == "LinkedIn"), "")
    github = next((link.url for link in all_links if link.label == "GitHub" and "github.com/" in link.url.lower()), "")
    portfolio = next(
        (
            link.url
            for link in all_links
            if link.label == "Portfolio"
        ),
        "",
    )

    phone_match = re.search(r"(?:\+?\d[\d ()-]{8,}\d)", clean)
    phone = re.sub(r"\s+", " ", phone_match.group(0)).strip() if phone_match else ""

    location = ""
    for line in lines[:12]:
        lower = line.lower()
        if any(token in lower for token in ("india", "bengaluru", "bangalore", "mumbai", "delhi", "pune", "mysuru", "karnataka")):
            if line != name and "@" not in line:
                location = line
                break

    skills: list[str] = []
    for value in re.split(r"[,|•;\n]", sec["skills"]):
        value = _clean_latex_markup(value).strip(" -:")
        if value and len(value) < 80 and value.lower() not in {x.lower() for x in skills}:
            skills.append(value)

    summary = sec["summary"]
    experience_lines = parse_bullets(sec["experience"])
    experience: list[Experience] = []
    if experience_lines:
        experience = [
            Experience(
                title="Professional Experience",
                bullets=experience_lines[:12],
            )
        ]

    projects = _parse_projects(sec["projects"], text)

    # PDF link annotations and LaTeX hrefs can be separated from visible
    # project labels by the extractor. Attach unassigned project/demo URLs
    # in source order so clickable links are not lost.
    project_level_links: list[ProjectLink] = []
    for link in all_links:
        lower = link.url.lower()
        if "linkedin" in lower or "portfolio" in lower:
            continue
        if "github.com/" in lower:
            match = re.search(r"github\.com/([^/?#]+)/?([^/?#]*)", lower)
            if match and match.group(2):
                project_level_links.append(link)
            continue
        if link.label == "Live Demo":
            project_level_links.append(link)
        elif link.label == "Project":
            project_level_links.append(link)
        elif any(token in lower for token in ("streamlit", "render.com", "vercel.app")):
            project_level_links.append(ProjectLink(label="Live Demo", url=link.url))

    link_cursor = 0
    for project in projects:
        if project.links:
            continue
        attached: list[ProjectLink] = []
        while link_cursor < len(project_level_links) and len(attached) < 2:
            candidate_link = project_level_links[link_cursor]
            link_cursor += 1
            if not any(existing.url == candidate_link.url for existing in attached):
                attached.append(candidate_link)
        if attached:
            project.links = attached
            project.url = attached[0].url

    education_lines = parse_bullets(sec["education"])
    education: list[Education] = []
    if education_lines:
        education.append(
            Education(
                institution=education_lines[0],
                field="; ".join(education_lines[1:3]),
            )
        )

    project_links = [link for project in projects for link in project.links]
    candidate_github = github
    if not candidate_github:
        for link in project_links:
            match = re.search(
                r"github\.com/([^/?#]+)/?([^/?#]*)",
                link.url.lower(),
            )
            if match and not match.group(2):
                candidate_github = link.url
                break

    return CandidateProfile(
        contact=Contact(
            name=name,
            email=emails[0] if emails else "",
            phone=phone,
            location=location,
            linkedin=linkedin,
            github=candidate_github,
            portfolio=portfolio,
        ),
        summary=summary,
        skills=skills,
        experience=experience,
        projects=projects,
        education=education,
        certifications=parse_bullets(sec["certifications"]),
        awards=parse_bullets(sec["awards"]),
        raw_text=clean,
        source_format=Path(filename).suffix.lower().lstrip(".") or "txt",
    )
