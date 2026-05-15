import sqlite3

def get_db_connection():
    conn = sqlite3.connect('crm.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name_ru TEXT NOT NULL,
            full_name_zh TEXT,
            passport TEXT NOT NULL,
            address TEXT,
            program TEXT NOT NULL,
            document_filename TEXT
        )
    ''')
    conn.commit()
    conn.close()