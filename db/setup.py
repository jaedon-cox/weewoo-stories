#!/usr/bin/env python3
"""Initialize the PostgreSQL database schema."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def setup():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with open(SCHEMA_PATH) as f:
        conn.cursor().execute(f.read())
    conn.commit()
    conn.close()
    print("Database schema initialized.")


if __name__ == "__main__":
    setup()
