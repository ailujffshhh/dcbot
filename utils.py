import re
import os
import PyPDF2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

def extract_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.strip()

def markdown_to_pdf(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', text)
    text = re.sub(r'^\s*---\s*$', '<hr/>', text, flags=re.MULTILINE)
    return text

def generate_formatted_pdf(text, output_file="reviewer.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor("#2E4053")
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        textColor=colors.black
    )
    elements = [Paragraph("Study Reviewer", title_style), Spacer(1, 12)]
    formatted_text = markdown_to_pdf(text)
    sections = formatted_text.split('<hr/>')
    for i, sec in enumerate(sections):
        for paragraph in sec.strip().split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                elements.append(Paragraph(paragraph, body_style))
                elements.append(Spacer(1, 4))
        if i < len(sections) - 1:
            elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
            elements.append(Spacer(1, 8))
    doc.build(elements)
    return output_file

def split_text(text, max_length=2000):
    parts = []
    while len(text) > max_length:
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:]
    if text:
        parts.append(text)
    return parts
