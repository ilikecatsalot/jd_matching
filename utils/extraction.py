import PyPDF2
import docx2txt
import sqlite3

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        return str(e)
    return text

def extract_text_from_docx(file_path):
    try:
        return docx2txt.process(file_path)
    except Exception as e:
        return str(e)

def extract_text_from_doc(file_path):
    try:
        import mammoth
        with open(file_path, 'rb') as file:
            result = mammoth.extract_raw_text(file)
            return result.value
    except Exception as e:
        return str(e)

def extract_text_from_rich_text(file_path):
    try:
        from striprtf.striprtf import rtf_to_text
        with open(file_path, 'r', encoding='utf-8') as file:
            rtf_content = file.read()
            text = rtf_to_text(rtf_content)
            return text
    except Exception as e:
        return str(e)