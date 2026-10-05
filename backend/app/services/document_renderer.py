from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from docx import Document
from docx.shared import Pt

def render_docx(resume: dict) -> bytes:
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    doc.add_heading(resume.get('name', 'Resume'), 0)
    if resume.get('contact_line'): doc.add_paragraph(resume['contact_line'])
    if resume.get('headline'): doc.add_paragraph(resume['headline'])
    sections = [('Professional Summary', 'summary'), ('Skills', 'skills'), ('Experience', 'experience'), ('Projects', 'projects'), ('Education', 'education'), ('Certifications', 'certifications')]
    for title, key in sections:
        values = resume.get(key)
        if not values: continue
        doc.add_heading(title, level=1)
        if key == 'summary': doc.add_paragraph(values)
        elif key == 'skills': doc.add_paragraph(', '.join(values))
        elif key == 'certifications':
            for value in values: doc.add_paragraph(value, style='List Bullet')
        elif key == 'experience':
            for item in values:
                doc.add_paragraph(f"{item.get('title','')} — {item.get('company','')}", style='Heading 2')
                if item.get('dates'): doc.add_paragraph(item['dates'])
                for bullet in item.get('bullets', []): doc.add_paragraph(bullet, style='List Bullet')
        elif key == 'projects':
            for item in values:
                doc.add_paragraph(item.get('name',''), style='Heading 2')
                if item.get('technologies'): doc.add_paragraph('Technologies: ' + ', '.join(item['technologies']))
                for bullet in item.get('bullets', []): doc.add_paragraph(bullet, style='List Bullet')
        elif key == 'education':
            for item in values:
                doc.add_paragraph(f"{item.get('degree','')} {item.get('field','')} — {item.get('institution','')}")
                if item.get('dates'): doc.add_paragraph(item['dates'])
    out = BytesIO(); doc.save(out); return out.getvalue()

def render_pdf(resume: dict) -> bytes:
    out = BytesIO(); styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=36)
    story = [Paragraph(resume.get('name', 'Resume'), styles['Title'])]
    if resume.get('contact_line'): story += [Paragraph(resume['contact_line'], styles['Normal']), Spacer(1, 8)]
    if resume.get('headline'): story.append(Paragraph(resume['headline'], styles['Heading2']))
    if resume.get('summary'): story += [Paragraph('PROFESSIONAL SUMMARY', styles['Heading2']), Paragraph(resume['summary'], styles['BodyText'])]
    for title, key in [('SKILLS','skills'),('EXPERIENCE','experience'),('PROJECTS','projects'),('EDUCATION','education'),('CERTIFICATIONS','certifications')]:
        values = resume.get(key) or []
        if not values: continue
        story.append(Paragraph(title, styles['Heading2']))
        if key in {'skills','certifications'}:
            story.append(Paragraph(', '.join(values), styles['BodyText']))
        else:
            for item in values:
                heading = f"{item.get('title','')} — {item.get('company','')}" if key == 'experience' else (item.get('name') or f"{item.get('degree','')} — {item.get('institution','')}")
                story.append(Paragraph(heading, styles['Heading3']))
                bullets = item.get('bullets', [])
                if bullets: story.append(ListFlowable([ListItem(Paragraph(b, styles['BodyText'])) for b in bullets], bulletType='bullet'))
    doc.build(story); return out.getvalue()
