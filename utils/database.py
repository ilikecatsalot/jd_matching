import sqlite3
import os
from datetime import datetime
from utils.common import generate_hash

def is_duplicate(file_hash):
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM resumes WHERE file_hash=?', (file_hash,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0


def save_resume_to_db(filename, filepath, file_hash):
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO resumes (filename, filepath, file_hash, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (filename, filepath, file_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_last_serial_number():
    if os.path.exists('last_uploaded_serial.txt'):
        with open('last_uploaded_serial.txt', 'r') as f:
            return int(f.read().strip())
    return 0

def save_last_serial_number(serial):
    with open('last_uploaded_serial.txt', 'w') as f:
        f.write(str(serial))
    
    
def is_duplicate_content(content_hash):
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM job_descriptions WHERE content_hash=?', (content_hash,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0

def save_jd_to_db(name, content):
    content_hash = generate_hash(content)
    
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    
    # Check if content is already in the database
    if is_duplicate_content(content_hash):
        return

    # Insert job description with content hash
    c.execute('INSERT INTO job_descriptions (name, content, content_hash) VALUES (?, ?, ?)', 
              (name, content, content_hash))
    conn.commit()
    conn.close()

    return "Job description saved successfully."