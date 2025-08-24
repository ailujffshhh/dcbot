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
    Remove invisible control characters that may cause issues.
    """
    return re.sub(r'[\x00-\x1F\x7F]', '', text)

def split_text(text: str, chunk_size: int = 1000) -> list[str]:
    """
    Split text into chunks of up to 1000 characters
    without breaking Markdown formatting (prefer newline/space).
    """
    text = clean_text(text)
    chunks = []
    
    while text:
        # Take a base chunk
        chunk = text[:chunk_size]

        if len(text) > chunk_size:
            # Prefer breaking at newline
            last_break = chunk.rfind("\n")
            if last_break == -1:
                # Fallback: break at space
                last_break = chunk.rfind(" ")
            if last_break != -1:
                chunk = chunk[:last_break]

        chunks.append(chunk)
        text = text[len(chunk):]  # continue with the rest
    
    return chunks


