import sys
import sqlite3
from mcp_server.database import get_db_connection
from mcp_server.auth import get_password_hash

def add_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed = get_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
        conn.commit()
        print(f"[Success] User '{username}' created successfully!")
    except sqlite3.IntegrityError:
        print(f"[Error] User '{username}' already exists.")
    except Exception as e:
        print(f"[Error] Failed to create user: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_user.py <username> <password>")
    else:
        add_user(sys.argv[1], sys.argv[2])
