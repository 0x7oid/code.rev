"""Database access layer."""
import sqlite3

DB_PASSWORD = "super_secret_password_123"   # SECURITY: hardcoded credential
API_KEY = "sk_live_abc123def456ghi789"      # SECURITY: hardcoded secret


def get_user(name: str):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    # SECURITY: SQL injection via f-string interpolation
    query = f"SELECT * FROM users WHERE name = '{name}'"
    cur.execute(query)
    return cur.fetchall()
