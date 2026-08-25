"""
database.py
-----------
Small SQLite persistence layer for the NL-to-SQL Streamlit app.

Handles:
    * user accounts (signup / login)
    * saved queries
    * feedback entries

No external dependencies beyond the Python standard library.
"""

import sqlite3
import hashlib
import hmac
import os
import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.db")


# --------------------------------------------------------------------------- #
# Connection helpers
# --------------------------------------------------------------------------- #
@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they do not already exist. Safe to call every run."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                natural_language TEXT,
                sql_query TEXT NOT NULL,
                explanation TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                sql_query TEXT,
                feedback_type TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


# --------------------------------------------------------------------------- #
# Password hashing (PBKDF2 - stdlib only, no extra dependency required)
# --------------------------------------------------------------------------- #
def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex()


def create_user(username: str, password: str) -> tuple[bool, str]:
    """Returns (success, message)."""
    username = username.strip()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)

    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, salt.hex(), datetime.datetime.utcnow().isoformat()),
            )
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def verify_user(username: str, password: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False
    salt = bytes.fromhex(row["salt"])
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, row["password_hash"])


def user_exists(username: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None


# --------------------------------------------------------------------------- #
# Saved queries
# --------------------------------------------------------------------------- #
def save_query(username: str, natural_language: str, sql_query: str, explanation: str = ""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO saved_queries (username, natural_language, sql_query, explanation, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (username, natural_language, sql_query, explanation, datetime.datetime.utcnow().isoformat()),
        )


def get_saved_queries(username: str, search: str = ""):
    with get_connection() as conn:
        if search:
            like = f"%{search}%"
            rows = conn.execute(
                """SELECT * FROM saved_queries WHERE username = ?
                   AND (natural_language LIKE ? OR sql_query LIKE ?)
                   ORDER BY created_at DESC""",
                (username, like, like),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM saved_queries WHERE username = ? ORDER BY created_at DESC",
                (username,),
            ).fetchall()
    return [dict(r) for r in rows]


def delete_query(query_id: int, username: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM saved_queries WHERE id = ? AND username = ?", (query_id, username)
        )


# --------------------------------------------------------------------------- #
# Feedback
# --------------------------------------------------------------------------- #
def add_feedback(username: str, sql_query: str, feedback_type: str, comment: str = ""):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO feedback (username, sql_query, feedback_type, comment, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (username, sql_query, feedback_type, comment, datetime.datetime.utcnow().isoformat()),
        )


def get_feedback(username: str = None):
    with get_connection() as conn:
        if username:
            rows = conn.execute(
                "SELECT * FROM feedback WHERE username = ? ORDER BY created_at DESC", (username,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]
