from html import escape
from io import BytesIO

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def _pdf_text(value) -> str:
    """Escape resume text before passing it to ReportLab's mini-HTML parser."""
    text = str(value or "")
    text = (
        text.replace("\\x00", "")
        .replace("\\r", "")
        .replace("\\u2028", " ")
        .replace("\\u2029", " ")
    )
    return escape(text).replace("\\n", "<br/>")


def render_docx(resume: dict) -> bytes:
    doc = Document()
    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(str(resume.get("name") or "Resume"), 0)

    if resume.get("contact_line"):
        doc.add_paragraph(str(resume["contact_line"]))
    if resume.get("headline"):
        doc.add_paragraph(str(resume["headline"]))

    sections = [
        ("Professional Summary", "summary"),
        ("Skills", "skills"),
        ("Experience", "experience"),
        ("Projects", "projects"),
        ("Education", "education"),
        ("Certifications", "certifications"),
    ]

    for title, key in sections:
        values = resume.get(key)
        if not values:
            continue

        doc.add_heading(title, level=1)

        if key == "summary":
            doc.add_paragraph(str(values))
        elif key == "skills":
            doc.add_paragraph(", ".join(str(x) for x in values))
        elif key == "certifications":
            for value in values:
                doc.add_paragraph(str(value), style="List Bullet")
        elif key == "experience":
            for item in values:
                doc.add_paragraph(
                    f"{item.get('title', '')} — {item.get('company', '')}",
                    style="Heading 2",
                )
                if item.get("dates"):
                    doc.add_paragraph(str(item["dates"]))
                for bullet in item.get("bullets", []):
                    doc.add_paragraph(str(bullet), style="List Bullet")
        elif key == "projects":
            for item in values:
                doc.add_paragraph(str(item.get("name", "")), style="Heading 2")
                if item.get("technologies"):
                    doc.add_paragraph(
                        "Technologies: "
                        + ", ".join(str(x) for x in item["technologies"])
                    )
                for bullet in item.get("bullets", []):
                    doc.add_paragraph(str(bullet), style="List Bullet")
        elif key == "education":
            for item in values:
                doc.add_paragraph(
                    f"{item.get('degree', '')} "
                    f"{item.get('field', '')} — "
                    f"{item.get('institution', '')}"
                )
                if item.get("dates"):
                    doc.add_paragraph(str(item["dates"]))

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def render_pdf(resume: dict) -> bytes:
    out = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=36,
        bottomMargin=36,
    )

    story = [Paragraph(_pdf_text(resume.get("name", "Resume")), styles["Title"])]

    if resume.get("contact_line"):
        story += [
            Paragraph(_pdf_text(resume["contact_line"]), styles["Normal"]),
            Spacer(1, 8),
        ]
    if resume.get("headline"):
        story.append(Paragraph(_pdf_text(resume["headline"]), styles["Heading2"]))
    if resume.get("summary"):
        story += [
            Paragraph("PROFESSIONAL SUMMARY", styles["Heading2"]),
            Paragraph(_pdf_text(resume["summary"]), styles["BodyText"]),
        ]

    for title, key in [
        ("SKILLS", "skills"),
        ("EXPERIENCE", "experience"),
        ("PROJECTS", "projects"),
        ("EDUCATION", "education"),
        ("CERTIFICATIONS", "certifications"),
    ]:
        values = resume.get(key) or []
        if not values:
            continue

        story.append(Paragraph(title, styles["Heading2"]))

        if key in {"skills", "certifications"}:
            story.append(
                Paragraph(
                    _pdf_text(", ".join(str(x) for x in values)),
                    styles["BodyText"],
                )
            )
            continue

        for item in values:
            if key == "experience":
                heading = (
                    f"{item.get('title', '')} — {item.get('company', '')}"
                )
            else:
                heading = item.get("name") or (
                    f"{item.get('degree', '')} — "
                    f"{item.get('institution', '')}"
                )

            story.append(Paragraph(_pdf_text(heading), styles["Heading3"]))

            bullets = item.get("bullets", [])
            if bullets:
                story.append(
                    ListFlowable(
                        [
                            ListItem(
                                Paragraph(_pdf_text(bullet), styles["BodyText"])
                            )
                            for bullet in bullets
                        ],
                        bulletType="bullet",
                    )
                )

    doc.build(story)
    return out.getvalue()
