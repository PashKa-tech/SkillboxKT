import sqlite3

DB_NAME = "users.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS allowgroups (
            groupid TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            name INTEGER,
            timekt INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_notifications (
            tgid TEXT,
            course TEXT,
            period TEXT,
            date_sent TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            tgid TEXT,
            group_ids TEXT,
            settings TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id TEXT PRIMARY KEY
        )
    ''')

    conn.commit()
    conn.close()
