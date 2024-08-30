from flask import Flask, request, render_template, jsonify, send_from_directory
from dotenv import load_dotenv
from datetime import datetime
import os
import re
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain import PromptTemplate 
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
import tempfile
import sqlite3
from utils.extraction import extract_text_from_pdf, extract_text_from_docx, extract_text_from_doc, extract_text_from_rich_text
from utils.database import is_duplicate, save_resume_to_db, get_last_serial_number, save_last_serial_number, save_jd_to_db, is_duplicate_content
from utils.preprocessing import clean_text, load_and_clean_documents
from utils.common import generate_hash

app = Flask(__name__)

class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata if metadata is not None else {}

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory('uploads', filename)


@app.route('/get_existing_jds', methods=['GET'])
def get_existing_jds():
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('SELECT id, name FROM job_descriptions')
    jds = c.fetchall()
    conn.close()
    return jsonify({'jds': [{'id': jd[0], 'name': jd[1]} for jd in jds]})

@app.route('/load_jd/<int:jd_id>', methods=['GET'])
def load_jd(jd_id):
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('SELECT content FROM job_descriptions WHERE id = ?', (jd_id,))
    jd = c.fetchone()
    conn.close()
    if jd:
        return jsonify({'content': jd[0]})
    return jsonify({'error': 'Job description not found'}), 404

@app.route('/delete_jd/<int:jd_id>', methods=['DELETE'])
def delete_jd(jd_id):
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('DELETE FROM job_descriptions WHERE id = ?', (jd_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'Job description deleted'})

@app.route('/check_jd_name', methods=['POST'])
def check_jd_name():
    jd_name = request.json.get('jd_name')
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM job_descriptions WHERE name = ?', (jd_name,))
    name_exists = c.fetchone()[0] > 0
    conn.close()
    return jsonify({'exists': name_exists})



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        files = request.files.getlist('files')
        jd_name = request.form['jd_name']

        if request.form['job_description_option'] == 'text':
            job_description = request.form['job_description']
        else:
            job_description_file = request.files['job_description_file']
            file_extension = os.path.splitext(job_description_file.filename)[1].lower()

            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                job_description_file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            # Extract text based on file extension
            if file_extension == ".pdf":
                job_description = extract_text_from_pdf(temp_file_path)
            elif file_extension == ".docx":
                job_description = extract_text_from_docx(temp_file_path)
            elif file_extension == ".doc":
                job_description = extract_text_from_doc(temp_file_path)
            elif file_extension == ".rtf":
                job_description = extract_text_from_rich_text(temp_file_path)
            
            else:
                job_description = "Unsupported file type"

            # Remove the temporary file after extraction
            os.remove(temp_file_path)

        save_jd_to_db(jd_name, job_description)

        top_k = int(request.form.get('top_k', 5))
        
        evaluation_date_start = request.form.get('evaluation_date_start')
        evaluation_date_end = request.form.get('evaluation_date_end')

        # Convert selected dates to datetime objects
        evaluation_date_start = datetime.strptime(evaluation_date_start, '%Y-%m-%d') if evaluation_date_start else None
        evaluation_date_end = datetime.strptime(evaluation_date_end, '%Y-%m-%d') if evaluation_date_end else None

        # Save uploaded files with new filenames
        pdf_directory = './uploads'
        os.makedirs(pdf_directory, exist_ok=True)

        last_serial_number = get_last_serial_number()

        for file in files:
            last_serial_number += 1
            new_filename = f"{last_serial_number}{os.path.splitext(file.filename)[1]}"
            new_filepath = os.path.join(pdf_directory, new_filename)
            file.save(new_filepath)

            # Extract and clean text
            if new_filename.endswith(".pdf"):
                text = extract_text_from_pdf(new_filepath)
            elif new_filename.endswith(".docx"):
                text = extract_text_from_docx(new_filepath)
            elif new_filename.endswith(".doc"):
                text = extract_text_from_doc(new_filepath)
            else:
                text = " "

            clean_doc = clean_text(text)

            # Hash the cleaned document
            file_hash = generate_hash(clean_doc)

            # Skip duplicate files
            if is_duplicate(file_hash):
                last_serial_number -= 1
                os.remove(new_filepath)
                continue

            # Save resume info to the database
            save_resume_to_db(new_filename, new_filepath, file_hash)

        # Update the last uploaded serial number
        save_last_serial_number(last_serial_number)

        # Filter resumes by the selected date range
        conn = sqlite3.connect('resume_database.db')
        c = conn.cursor()
        
        if evaluation_date_start and evaluation_date_end:
            c.execute("SELECT filename, filepath FROM resumes WHERE timestamp BETWEEN ? AND ?", 
                    (evaluation_date_start, evaluation_date_end))
        elif evaluation_date_start:
            c.execute("SELECT filename, filepath FROM resumes WHERE timestamp >= ?", 
                    (evaluation_date_start,))
        elif evaluation_date_end:
            c.execute("SELECT filename, filepath FROM resumes WHERE timestamp <= ?", 
                    (evaluation_date_end,))
        else:
            c.execute("SELECT filename, filepath FROM resumes")
            
        filtered_resumes = c.fetchall()
        conn.close()
        # Load and clean only the filtered documents
        documents = []
        for filename, filepath in filtered_resumes:
            if filename.endswith(".pdf"):
                text = extract_text_from_pdf(filepath)
            elif filename.endswith(".docx"):
                text = extract_text_from_docx(filepath)
            elif filename.endswith(".doc"):
                text = extract_text_from_doc(filepath)

            clean_doc = clean_text(text)
            if len(clean_doc) == 0:
                continue
            else:
                metadata = {"source": filename}
                documents.append(Document(page_content=f"filename = {filename} {clean_doc}", metadata=metadata))

        # Generate embeddings and create a vector store
        embedding_model = SentenceTransformerEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        db = FAISS.from_documents(documents, embedding_model)
        file_path = "saved_embeddings"
        db.save_local(file_path)

        # Reload the documents from the vector store
        new_db = FAISS.load_local(folder_path=file_path, embeddings=embedding_model, allow_dangerous_deserialization=True)
        retriever = new_db.as_retriever(search_kwargs={"k": top_k})

        # Initialize LLM
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0.3, top_p=0.85)
        chain = RetrievalQAWithSourcesChain.from_llm(llm=llm, retriever=retriever)

        # Process the job description
        job_description = re.sub(r'\n', ' ', job_description)
        job_description = re.sub(r'\s+', ' ', job_description)
        job_description = job_description.lower()

        # Convert job description to embedding
        job_description_embedding = embedding_model.embed_query(job_description)

        prompt = """
        ### You are a helpful AI assistant with advanced knowledge in technology.
        You are given multiple resumes of different candidates separated by '\n$$$$$\n' in a string format.
        Your role is to evaluate a candidate's resume meticulously based on the provided job description.

        ### Your evaluation should be thorough, precise, and objective, ensuring that the most
        qualified candidates are accurately identified based on their resume content in relation
        to the job criteria. 

        ### Evaluation Output:
        Strictly follow the format provided below without any deviation. Do not add any extra text, comments, symbols or summaries beyond what is required.

        Show the {top_k} resumes corresponding to their matching percentage. Briefly describe each of the top candidates in relevance to the Job Description. Bold only the technologies that matches exactly with the Job Description.

        1. Filename: [Write the filename found here.]
        2. Name: [Give the candidate's name if found in the resume. If name is not found write "Undefined"]
        3. Match Percentage: [Calculate the percentage of match between the resume and the job description. Add a "%" symbol at the end]
        4. Strengths: [Describe and emphasize their skillset, education, and experience that match or are related to the job description.]
        5. Weaknesses: [Describe and emphasize the skills, education, or experience mentioned in the job description that do not match the candidate's resume.]

        job_description={jd}
        resume={text}

        Do not give a conclusion or any other text after the resume evaluations. Strictly adhere to the above format.
        """


        llm_prompt = PromptTemplate.from_template(prompt)
        rag_chain = (
            {"jd": lambda x: job_description, "text": RunnablePassthrough(), "top_k": lambda x: top_k}
            | llm_prompt
            | llm
            | StrOutputParser()
        )

        # Fetch the resumes from the retriever using the job description embedding
        resumes = retriever.get_relevant_documents(str(job_description_embedding), k=top_k)

        # Combine the resumes into a single string separated by '$$$$$'
        resumes_str = "\n$$$$$\n".join([doc.page_content for doc in resumes])

        # Run the evaluation chain
        result = rag_chain.invoke({"text": resumes_str})
        print(result)

        evaluations = result.split("1. Filename: ")

        response = []
        for evaluation in evaluations:
            if evaluation.strip():
                filename_match = re.search(r'\d+\.pdf', evaluation)
                if filename_match:
                    filename = filename_match.group(0)

                    conn = sqlite3.connect('resume_database.db')
                    c = conn.cursor()
                    c.execute("SELECT filepath FROM resumes WHERE filename=?", (filename,))
                    row = c.fetchone()
                    conn.close()
                    if row:
                        filepath = row[0]
                        response.append({
                            "filename": filename,
                            "text": evaluation.strip(),
                            "filepath": filepath
                        })

        return jsonify(result=response)

    return render_template('index.html')


