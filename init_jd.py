import sqlite3

def init_jd():
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('''
CREATE TABLE IF NOT EXISTS job_descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    content_hash TEXT NOT NULL
)            
        
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_jd()
