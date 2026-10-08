"""SQLite shared by the API and the worker (separate processes)."""
import os
import sqlite3

PATH = os.environ.get("NCII_DB", "ncii.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS hashes(
  id INTEGER PRIMARY KEY, user TEXT NOT NULL, h TEXT NOT NULL, UNIQUE(user, h));
CREATE TABLE IF NOT EXISTS matches(
  id INTEGER PRIMARY KEY, hash_id INTEGER NOT NULL, user TEXT NOT NULL,
  source_url TEXT NOT NULL, distance INTEGER NOT NULL, found_at REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending -> confirmed | rejected (by the registered user)
  owns_copyright INTEGER NOT NULL DEFAULT 0, UNIQUE(hash_id, source_url));
CREATE TABLE IF NOT EXISTS notices(
  id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, kind TEXT NOT NULL,
  recipient TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL,
  UNIQUE(match_id, kind));
"""


def db() -> sqlite3.Connection:
    c = sqlite3.connect(PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c
