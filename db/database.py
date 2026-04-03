import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


def get_connection():
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Stories ---

def insert_story(story_id, category, title, body):
    with db() as conn:
        conn.cursor().execute(
            "INSERT INTO stories (id, category, title, body, status) VALUES (%s, %s, %s, %s, 'pending_tts')",
            (story_id, category, title, body),
        )


def update_story_status(story_id, status):
    with db() as conn:
        conn.cursor().execute("UPDATE stories SET status = %s WHERE id = %s", (status, story_id))


def get_story(story_id):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stories WHERE id = %s", (story_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_stories_by_status(status):
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM stories WHERE status = %s", (status,))
        return [dict(r) for r in cur.fetchall()]


# --- Parts ---

def insert_part(part_id, story_id, part_number, file_path, scheduled_at):
    with db() as conn:
        conn.cursor().execute(
            """INSERT INTO parts (id, story_id, part_number, file_path, status, scheduled_at)
               VALUES (%s, %s, %s, %s, 'queued', %s)""",
            (part_id, story_id, part_number, file_path, scheduled_at),
        )


def update_part_status(part_id, status, **kwargs):
    fields = ["status = %s"]
    values = [status]
    for k, v in kwargs.items():
        fields.append(f"{k} = %s")
        values.append(v)
    values.append(part_id)
    with db() as conn:
        conn.cursor().execute(
            f"UPDATE parts SET {', '.join(fields)} WHERE id = %s", values
        )


def get_parts_due(now_iso):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            """SELECT * FROM parts
               WHERE status = 'queued' AND scheduled_at <= %s
               ORDER BY scheduled_at ASC
               FOR UPDATE SKIP LOCKED""",
            (now_iso,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_parts_by_story(story_id):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM parts WHERE story_id = %s ORDER BY part_number ASC",
            (story_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_posted_parts():
    with db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, file_path FROM parts WHERE status = 'posted'")
        return [dict(r) for r in cur.fetchall()]


def increment_retry(part_id):
    with db() as conn:
        conn.cursor().execute(
            "UPDATE parts SET retry_count = retry_count + 1, status = 'queued' WHERE id = %s",
            (part_id,),
        )
