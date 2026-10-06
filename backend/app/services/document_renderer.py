import re
import unicodedata
from html import escape
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable, Paragraph, PageBreak, SimpleDocTemplate
from pypdf import PdfReader

URL_RE = re.compile(r"https?://[^\s|]+|www\.[^\s|]+", re.I)


def _normalise_text(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    replacements = {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "-",
        "\u00a0": " ",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\ufeff": "",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.replace("\x00", "").replace("\r", "").strip()


def _url(value: str) -> str:
    value = value.strip().rstrip(".,;)")
    if value.startswith("www."):
        return "https://" + value
    return value


def _pdf_rich_text(value) -> str:
    text = _normalise_text(value)
    chunks = []
    cursor = 0

    for match in URL_RE.finditer(text):
        before = text[cursor:match.start()]
        if before:
            chunks.append(escape(before).replace("\n", "<br/>"))

        url = _url(match.group(0))
        href = escape(url, quote=True)
        chunks.append(
            f'<link href="{href}" color="#111827"><u>{escape(url)}</u></link>'
        )
        cursor = match.end()

    tail = text[cursor:]
    if tail:
        chunks.append(escape(tail).replace("\n", "<br/>"))

    return "".join(chunks)


def _add_hyperlink(paragraph, text: str, url: str):
    url = _url(url)
    relationship_id = paragraph.part.relate_to(
        url,
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
        is_external=True,
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)

    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "16478E")
    properties.append(color)

    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    properties.append(underline)

    run.append(properties)

    text_element = OxmlElement("w:t")
    text_element.text = text
    run.append(text_element)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _add_rich_docx_paragraph(paragraph, value):
    text = _normalise_text(value)
    cursor = 0

    for match in URL_RE.finditer(text):
        before = text[cursor:match.start()]
        if before:
            paragraph.add_run(before)

        url = _url(match.group(0))
        _add_hyperlink(paragraph, url, url)
        cursor = match.end()

    tail = text[cursor:]
    if tail:
        paragraph.add_run(tail)


def _section(story, title, style):
    story.append(Paragraph(escape(title.upper()), style))
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color="#16478E",
            spaceBefore=1,
            spaceAfter=4,
        )
    )


def _layout_profile(page_target: int = 1, style: str = "reference") -> dict:
    """Return typography/spacing settings for a target page count."""
    page_target = 2 if int(page_target) == 2 else 1
    style = (style or "reference").strip().lower()
    if style not in {"reference", "compact"}:
        style = "reference"

    if style == "compact":
        return {
            "right": 26,
            "left": 26,
            "top": 22,
            "bottom": 24,
            "title": 16,
            "title_leading": 17.5,
            "contact": 7.0,
            "contact_leading": 8.1,
            "headline": 9.1,
            "headline_leading": 10.1,
            "section": 9.1,
            "section_leading": 9.7,
            "body": 7.25,
            "body_leading": 8.55,
            "entry": 7.75,
            "entry_leading": 8.85,
            "small": 6.9,
            "small_leading": 7.8,
            "section_space": 4.0,
            "bullet_space": 1.0,
        }

    if page_target == 1:
        # Default one-page reference profile: close to the supplied CV image.
        return {
            "right": 30,
            "left": 30,
            "top": 24,
            "bottom": 26,
            "title": 17,
            "title_leading": 18.5,
            "contact": 7.2,
            "contact_leading": 8.4,
            "headline": 9.4,
            "headline_leading": 10.5,
            "section": 9.4,
            "section_leading": 10.0,
            "body": 7.75,
            "body_leading": 9.15,
            "entry": 8.15,
            "entry_leading": 9.3,
            "small": 7.25,
            "small_leading": 8.2,
            "section_space": 4.5,
            "bullet_space": 1.2,
        }

    return {
        "right": 36,
        "left": 36,
        "top": 28,
        "bottom": 30,
        "title": 18,
        "title_leading": 20,
        "contact": 8.2,
        "contact_leading": 10,
        "headline": 10.5,
        "headline_leading": 12,
        "section": 10.2,
        "section_leading": 11,
        "body": 8.8,
        "body_leading": 10.7,
        "entry": 9.2,
        "entry_leading": 11,
        "small": 8.2,
        "small_leading": 9.6,
        "section_space": 6,
        "bullet_space": 2,
    )


def _render_pdf_once(
    resume: dict,
    page_target: int,
    style: str,
    force_two_page_break: bool = False,
) -> bytes:
    out = BytesIO()
    p = _layout_profile(page_target, style)

    title = ParagraphStyle(
        "CVTitle", fontName="Helvetica-Bold",
        fontSize=p["title"], leading=p["title_leading"],
        textColor="#16478E", alignment=1, spaceAfter=3,
    )
    contact = ParagraphStyle(
        "CVContact", fontName="Helvetica",
        fontSize=p["contact"], leading=p["contact_leading"],
        alignment=1, spaceAfter=3,
    )
    headline = ParagraphStyle(
        "CVHeadline", fontName="Helvetica-Bold",
        fontSize=p["headline"], leading=p["headline_leading"],
        alignment=1, spaceAfter=5 if page_target == 1 else 7,
    )
    section = ParagraphStyle(
        "CVSection", fontName="Helvetica-Bold",
        fontSize=p["section"], leading=p["section_leading"],
        textColor="#16478E", spaceBefore=p["section_space"], spaceAfter=0,
    )
    body = ParagraphStyle(
        "CVBody", fontName="Helvetica",
        fontSize=p["body"], leading=p["body_leading"],
        spaceAfter=p["bullet_space"],
    )
    entry = ParagraphStyle(
        "CVEntry", fontName="Helvetica",
        fontSize=p["entry"], leading=p["entry_leading"],
        spaceBefore=1.5, spaceAfter=1,
    )
    small = ParagraphStyle(
        "CVSmall", fontName="Helvetica",
        fontSize=p["small"], leading=p["small_leading"],
        textColor="#333333", spaceAfter=p["bullet_space"],
    )

    doc = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=p["right"],
        leftMargin=p["left"],
        topMargin=p["top"],
        bottomMargin=p["bottom"],
        title=_normalise_text(resume.get("name", "Resume")),
        author="CVForge",
    )

    story = [
        Paragraph(escape(_normalise_text(resume.get("name", "Resume"))), title),
        Paragraph(_pdf_rich_text(resume.get("contact_line", "")), contact),
    ]

    professional_links = resume.get("professional_links") or []
    if professional_links:
        link_parts = []
        for link in professional_links:
            label = _normalise_text(link.get("label", "Link"))
            url = _url(_normalise_text(link.get("url", "")))
            if url:
                link_parts.append(
                    f'<link href="{escape(url, quote=True)}" color="#000000">'
                    f'<u>{escape(label)}</u></link>'
                )
        if link_parts:
            story.append(Paragraph(" | ".join(link_parts), contact))

    if resume.get("headline"):
        story.append(
            Paragraph(escape(_normalise_text(resume["headline"])), headline)
        )

    if resume.get("summary"):
        _section(story, "Professional Summary", section)
        story.append(Paragraph(_pdf_rich_text(resume["summary"]), body))

    if resume.get("skill_groups"):
        _section(story, "Technical Skills", section)
        for group, values in resume["skill_groups"].items():
            if values:
                text = ", ".join(_normalise_text(x) for x in values)
                story.append(
                    Paragraph(
                        f"<b>{escape(_normalise_text(group))}:</b> "
                        f"{_pdf_rich_text(text)}",
                        body,
                    )
                )
    elif resume.get("skills"):
        _section(story, "Technical Skills", section)
        story.append(
            Paragraph(
                _pdf_rich_text(", ".join(_normalise_text(x) for x in resume["skills"])),
                body,
            )
        )

    if resume.get("experience"):
        _section(story, "Experience", section)
        for item in resume["experience"]:
            title_text = _normalise_text(item.get("title", ""))
            company = _normalise_text(item.get("company", ""))
            dates = _normalise_text(item.get("dates", ""))
            location = _normalise_text(item.get("location", ""))
            right = " | ".join(x for x in (dates, location) if x)
            heading = escape(
                " - ".join(x for x in (title_text, company) if x)
            )
            if right:
                heading += f' <font color="#444444">| {escape(right)}</font>'
            story.append(Paragraph(heading, entry))
            for bullet in item.get("bullets", []):
                story.append(Paragraph("- " + _pdf_rich_text(bullet), body))

    if resume.get("projects"):
        _section(story, "Selected Data Science Projects", section)
        for item in resume["projects"]:
            name = _normalise_text(item.get("name", ""))
            url = _normalise_text(item.get("url", ""))
            project_heading = f"<b><i>{escape(name)}</i></b>"
            links = item.get("links") or []
            if links:
                for link in links:
                    label = _normalise_text(link.get("label", "Project"))
                    clean_url = _url(_normalise_text(link.get("url", "")))
                    if clean_url:
                        project_heading += (
                            f' | <link href="{escape(clean_url, quote=True)}" '
                            f'color="#000000"><u>{escape(label)}</u></link>'
                        )
            elif url:
                clean_url = _url(url)
                project_heading += (
                    f' | <link href="{escape(clean_url, quote=True)}" '
                    f'color="#000000"><u>Project</u></link>'
                )
            story.append(Paragraph(project_heading, entry))
            technologies = item.get("technologies") or []
            if technologies:
                tech = ", ".join(_normalise_text(x) for x in technologies)
                story.append(
                    Paragraph("<i>Technologies: </i>" + _pdf_rich_text(tech), small)
                )
            for bullet in item.get("bullets", []):
                story.append(Paragraph("- " + _pdf_rich_text(bullet), body))

    if resume.get("education"):
        if page_target == 2 and force_two_page_break:
            story.append(PageBreak())
        _section(story, "Education", section)
        for item in resume["education"]:
            degree = _normalise_text(item.get("degree", ""))
            field = _normalise_text(item.get("field", ""))
            institution = _normalise_text(item.get("institution", ""))
            dates = _normalise_text(item.get("dates", ""))
            line = " ".join(x for x in (degree, field) if x)
            line = " - ".join(x for x in (line, institution) if x)
            if dates:
                line += f" | {dates}"
            story.append(Paragraph(f"<b>{escape(line)}</b>", entry))

    if resume.get("certifications"):
        _section(story, "Certifications", section)
        for item in resume["certifications"]:
            story.append(Paragraph("- " + _pdf_rich_text(item), body))

    doc.build(story)
    return out.getvalue()


def render_pdf(
    resume: dict,
    page_target: int = 1,
    style: str = "reference",
) -> bytes:
    """Render a one- or two-page ATS-friendly CV in the chosen layout."""
    page_target = 2 if int(page_target) == 2 else 1
    style = (style or "reference").strip().lower()
    if style not in {"reference", "compact"}:
        style = "reference"

    # For one-page requests, start compact. For two-page requests, use the
    # reference spacing. A second compact pass is a safety valve for unusually
    # dense resumes.
    attempts = [style]
    if page_target == 1 and style != "compact":
        attempts = ["reference", "compact"]
    elif page_target == 2 and style == "reference":
        attempts = ["reference", "compact"]

    best = None
    for attempt_style in attempts:
        payload = _render_pdf_once(
            resume,
            page_target,
            attempt_style,
            force_two_page_break=False,
        )
        pages = len(PdfReader(BytesIO(payload)).pages)

        # If the user explicitly requested two pages and the document is short
        # enough to fit on one, deliberately split before Education. This keeps
        # the requested two-page format without adding a forced blank final page.
        if page_target == 2 and pages == 1 and resume.get("education"):
            forced = _render_pdf_once(
                resume,
                page_target,
                attempt_style,
                force_two_page_break=True,
            )
            forced_pages = len(PdfReader(BytesIO(forced)).pages)
            if forced_pages <= 2:
                return forced
            payload = forced
            pages = forced_pages

        best = payload
        if pages <= page_target:
            return payload

    return best

def render_docx(resume: dict, page_target: int = 1, style: str = "reference") -> bytes:
    page_target = 2 if int(page_target) == 2 else 1
    style = (style or "reference").strip().lower()
    if style not in {"reference", "compact"}:
        style = "reference"

    doc = Document()
    section = doc.sections[0]
    if page_target == 1 or style == "compact":
        section.top_margin = Inches(0.38)
        section.bottom_margin = Inches(0.38)
        section.left_margin = Inches(0.50)
        section.right_margin = Inches(0.50)
        normal_size = 8.3
        name_size = 17
        heading_size = 9.2
    else:
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.left_margin = Inches(0.55)
        section.right_margin = Inches(0.55)
        normal_size = 9
        name_size = 18
        heading_size = 10

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(normal_size)

    name = doc.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = name.add_run(_normalise_text(resume.get("name", "Resume")))
    run.bold = True
    run.font.size = Pt(name_size)
    run.font.color.rgb = RGBColor(22, 71, 142)

    if resume.get("contact_line"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _add_rich_docx_paragraph(p, resume["contact_line"])

    professional_links = resume.get("professional_links") or []
    if professional_links:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for index, link in enumerate(professional_links):
            if index:
                p.add_run(" | ")
            label = _normalise_text(link.get("label", "Link"))
            url = _url(_normalise_text(link.get("url", "")))
            if url:
                _add_hyperlink(p, label, url)

    if resume.get("headline"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(_normalise_text(resume["headline"]))
        run.bold = True
        run.font.size = Pt(heading_size)

    def heading(text):
        p = doc.add_paragraph()
        run = p.add_run(text.upper())
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(22, 71, 142)
        p.paragraph_format.space_before = Pt(4 if page_target == 1 else 6)
        p.paragraph_format.space_after = Pt(1)

    if resume.get("summary"):
        heading("Professional Summary")
        doc.add_paragraph(_normalise_text(resume["summary"]))

    if resume.get("skill_groups"):
        heading("Technical Skills")
        for group, values in resume["skill_groups"].items():
            if not values:
                continue
            p = doc.add_paragraph()
            r = p.add_run(f"{_normalise_text(group)}: ")
            r.bold = True
            p.add_run(", ".join(_normalise_text(x) for x in values))
    elif resume.get("skills"):
        heading("Technical Skills")
        doc.add_paragraph(
            ", ".join(_normalise_text(x) for x in resume["skills"])
        )

    if resume.get("experience"):
        heading("Professional Experience")
        for item in resume["experience"]:
            p = doc.add_paragraph()
            r = p.add_run(
                " - ".join(
                    x
                    for x in (
                        _normalise_text(item.get("title", "")),
                        _normalise_text(item.get("company", "")),
                    )
                    if x
                )
            )
            r.bold = True

            right = " | ".join(
                x
                for x in (
                    _normalise_text(item.get("dates", "")),
                    _normalise_text(item.get("location", "")),
                )
                if x
            )
            if right:
                p.add_run(" | " + right)

            for bullet in item.get("bullets", []):
                p = doc.add_paragraph(style="List Bullet")
                _add_rich_docx_paragraph(p, bullet)

    if resume.get("projects"):
        heading("Selected Projects")
        for item in resume["projects"]:
            p = doc.add_paragraph()
            r = p.add_run(_normalise_text(item.get("name", "")))
            r.bold = True
            r.italic = True

            links = item.get("links") or []
            if links:
                for link in links:
                    url = _url(_normalise_text(link.get("url", "")))
                    label = _normalise_text(link.get("label", "Project"))
                    if url:
                        p.add_run(" | ")
                        _add_hyperlink(p, label, url)
            else:
                url = _normalise_text(item.get("url", ""))
                if url:
                    p.add_run(" | ")
                    clean_url = _url(url)
                    _add_hyperlink(p, "Project", clean_url)

            technologies = item.get("technologies") or []
            if technologies:
                p = doc.add_paragraph()
                r = p.add_run("Technologies: ")
                r.italic = True
                p.add_run(
                    ", ".join(_normalise_text(x) for x in technologies)
                )

            for bullet in item.get("bullets", []):
                p = doc.add_paragraph(style="List Bullet")
                _add_rich_docx_paragraph(p, bullet)

    if resume.get("education"):
        heading("Education")
        for item in resume["education"]:
            text = " ".join(
                x
                for x in (
                    _normalise_text(item.get("degree", "")),
                    _normalise_text(item.get("field", "")),
                )
                if x
            )
            line = " - ".join(
                x
                for x in (
                    text,
                    _normalise_text(item.get("institution", "")),
                )
                if x
            )
            if item.get("dates"):
                line += " | " + _normalise_text(item["dates"])

            p = doc.add_paragraph()
            r = p.add_run(line)
            r.bold = True

    if resume.get("certifications"):
        heading("Certifications")
        for item in resume["certifications"]:
            p = doc.add_paragraph(style="List Bullet")
            _add_rich_docx_paragraph(p, item)

    out = BytesIO()
    doc.save(out)
    return out.getvalue()
