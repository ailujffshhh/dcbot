import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import PyPDF2

def extract_pdf_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    return text.strip()

def generate_formatted_pdf(text, output_file="reviewer.pdf"):
    doc = SimpleDocTemplate(output_file, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=20, alignment=1, textColor=colors.HexColor("#2E4053"))
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=12, leading=16, textColor=colors.black)
    elements = [Paragraph("Study Reviewer", title_style), Spacer(1, 12)]
    sections = text.split("\n\n")
    for sec in sections:
        for paragraph in sec.split("\n"):
            paragraph = paragraph.strip()
            if paragraph:
                elements.append(Paragraph(paragraph, body_style))
                elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        elements.append(Spacer(1, 8))
    doc.build(elements)
    return output_file
    
import re

import re

def clean_text(text: str) -> str:
    """
    Clean up text by stripping whitespace and removing extra newlines.
    """
    if not text:
        return ""
    # Remove leading/trailing whitespace and collapse multiple newlines
    cleaned = re.sub(r'\n+', '\n', text.strip())
    return cleaned


def split_text(text: str, max_length: int = 2000) -> list[str]:
    """
    Split text into chunks that fit within Discord's 2000-character limit.
    """
    if not text:
        return []

    chunks = []
    while len(text) > max_length:
        # Find last newline within limit
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:  # No newline found, hard cut
            split_at = max_length

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    return chunks

