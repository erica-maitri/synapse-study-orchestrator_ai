import sqlite3
import os
import datetime
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "synapse.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    """)

    # Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        importance INTEGER NOT NULL,
        urgency INTEGER NOT NULL,
        score REAL DEFAULT 0.0,
        quadrant TEXT NOT NULL,
        estimated_duration INTEGER DEFAULT 30,
        due_date TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)

    # Calendar Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        task_id INTEGER,
        is_completed INTEGER DEFAULT 0,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """)

    # Flashcards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        front TEXT NOT NULL,
        back TEXT NOT NULL,
        subject TEXT DEFAULT 'General',
        image TEXT,
        repetitions INTEGER DEFAULT 0,
        interval_days INTEGER DEFAULT 1,
        ease_factor REAL DEFAULT 2.5,
        next_review_date TEXT NOT NULL
    )
    """)

    # Review Streaks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_streaks (
        date TEXT PRIMARY KEY,
        cards_reviewed INTEGER DEFAULT 0,
        cards_correct INTEGER DEFAULT 0,
        streak_count INTEGER DEFAULT 0
    )
    """)

    # Check if subject and image columns exist in flashcards (migration for existing DBs)
    cursor.execute("PRAGMA table_info(flashcards)")
    columns = [col[1] for col in cursor.fetchall()]
    if "subject" not in columns:
        cursor.execute("ALTER TABLE flashcards ADD COLUMN subject TEXT DEFAULT 'General'")
        conn.commit()
    if "image" not in columns:
        cursor.execute("ALTER TABLE flashcards ADD COLUMN image TEXT")
        conn.commit()

    # Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        parameters TEXT,
        status TEXT NOT NULL,
        error TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed default user if not exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        password = "password123"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", hashed))
        conn.commit()
        print("[DB] Initialized database and seeded default user: admin / password123")

    conn.close()

if __name__ == "__main__":
    init_db()
