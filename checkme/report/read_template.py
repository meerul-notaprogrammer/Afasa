
from docx import Document

def list_headers(docx_file):
    try:
        doc = Document(docx_file)
        print(f"--- Structure of {docx_file} ---")
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading') or para.style.name == 'Title':
                print(f"[{para.style.name}] {para.text}")
            # Also capture bold text that might look like a header but uses Normal style
            elif para.style.name == 'Normal' and len(para.text) < 50 and any(run.bold for run in para.runs):
                 print(f"[Potential Header] {para.text}")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == '__main__':
    list_headers('TEMPLATE INDUSTRIAL TRAINING REPORT _ UPDATE OCT 2024.docx')
