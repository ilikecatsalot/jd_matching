import sqlite3

def init_db():
    conn = sqlite3.connect('resume_database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            filepath TEXT,
            file_hash TEXT,
            timestamp TEXT             
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
