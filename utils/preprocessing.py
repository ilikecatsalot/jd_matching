import re
import os

def clean_text(text):

    # Convert to lowercase
    text = text.lower()
    
    # Remove emails
    text = re.sub(r'\S*@\S*\s?', '', text)
    
    # Remove phone numbers
    text = re.sub(r'\S*\d\S*\s?', '', text)
    
    # Remove special characters and non-alphanumeric characters
    text = re.sub(r'[^\w\s]', '', text)
    # Encode to ASCII and ignore non-ASCII characters
    text = text.encode("ascii", "ignore").decode()
    # Remove newlines and extra spaces
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text) 
    return text.strip()

def load_and_clean_documents(directory):
    documents = []
    for filename in os.listdir(directory):
        if filename.endswith((".pdf", ".docx", ".doc")):
            file_path = os.path.join(directory, filename)
            if filename.endswith(".pdf"):
                text = extract_text_from_pdf(file_path)
            elif filename.endswith(".docx"):
                text = extract_text_from_docx(file_path)
            elif filename.endswith(".doc"):
                text = extract_text_from_doc(file_path)
            
            clean_doc = clean_text(text)
            if len(clean_doc) == 0:
                continue
            else:
                metadata = {"source": filename}
                documents.append(Document(page_content=f"filename = {filename} {clean_doc}", metadata=metadata))
    return documents