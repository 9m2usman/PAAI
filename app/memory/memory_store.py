
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
# STEP 1: Define the database location

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "paai_memory.db"

@contextmanager
def database_connection(db_path):
    connection = sqlite3.connect(db_path)

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

# STEP 2: Initialize the database

def initialize_memory_db(db_path=DATABASE_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with database_connection(db_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, memory_key)
            )
        """)


# STEP 3: Validate user identity

def validate_user_id(user_id):
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid user_id is required.")


# STEP 4: Save or update a user profile

def save_user_profile(user_id, profile, db_path=DATABASE_PATH):
    validate_user_id(user_id)

    if not isinstance(profile, dict):
        raise ValueError("Profile must be a dictionary.")

    initialize_memory_db(db_path)

    profile_json = json.dumps(profile)
    updated_at = datetime.now(timezone.utc).isoformat()

    with database_connection(db_path) as connection:
        connection.execute("""
            INSERT INTO user_profiles (user_id, profile_data, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
                profile_data = excluded.profile_data,
                updated_at = excluded.updated_at
        """, (user_id, profile_json, updated_at))


# STEP 5: Retrieve a user profile

def get_user_profile(user_id, db_path=DATABASE_PATH):
    validate_user_id(user_id)
    initialize_memory_db(db_path)

    with database_connection(db_path) as connection:
        result = connection.execute("""
            SELECT profile_data
            FROM user_profiles
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    if result is None:
        return {}

    return json.loads(result[0])


# STEP 6: Save or update an individual memory

def save_memory(user_id, memory_key, memory_value,
                category="general", db_path=DATABASE_PATH):

    validate_user_id(user_id)

    if not isinstance(memory_key, str) or not memory_key.strip():
        raise ValueError("A valid memory key is required.")

    if not isinstance(memory_value, str) or not memory_value.strip():
        raise ValueError("A valid memory value is required.")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("A valid memory category is required.")

    initialize_memory_db(db_path)

    updated_at = datetime.now(timezone.utc).isoformat()

    with database_connection(db_path) as connection:
        connection.execute("""
            INSERT INTO user_memories
            (user_id, memory_key, memory_value, category, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, memory_key)
            DO UPDATE SET
                memory_value = excluded.memory_value,
                category = excluded.category,
                updated_at = excluded.updated_at
        """, (
            user_id,
            memory_key,
            memory_value,
            category,
            updated_at
        ))


# STEP 7: Retrieve one memory

def get_memory(user_id, memory_key, db_path=DATABASE_PATH):
    validate_user_id(user_id)
    initialize_memory_db(db_path)

    with database_connection(db_path) as connection:
        result = connection.execute("""
            SELECT memory_key, memory_value, category, updated_at
            FROM user_memories
            WHERE user_id = ? AND memory_key = ?
        """, (user_id, memory_key)).fetchone()

    if result is None:
        return None

    return {
        "key": result[0],
        "value": result[1],
        "category": result[2],
        "updated_at": result[3]
    }


# STEP 8: Retrieve all memories belonging to a user

def get_user_memories(user_id, category=None, db_path=DATABASE_PATH):
    validate_user_id(user_id)
    initialize_memory_db(db_path)

    with database_connection(db_path) as connection:

        if category is None:
            results = connection.execute("""
                SELECT memory_key, memory_value, category, updated_at
                FROM user_memories
                WHERE user_id = ?
                ORDER BY id
            """, (user_id,)).fetchall()

        else:
            results = connection.execute("""
                SELECT memory_key, memory_value, category, updated_at
                FROM user_memories
                WHERE user_id = ? AND category = ?
                ORDER BY id
            """, (user_id, category)).fetchall()

    return [
        {
            "key": row[0],
            "value": row[1],
            "category": row[2],
            "updated_at": row[3]
        }
        for row in results
    ]


# STEP 9: Delete an individual memory

def delete_memory(user_id, memory_key, db_path=DATABASE_PATH):
    validate_user_id(user_id)
    initialize_memory_db(db_path)

    with database_connection(db_path) as connection:
        cursor = connection.execute("""
            DELETE FROM user_memories
            WHERE user_id = ? AND memory_key = ?
        """, (user_id, memory_key))

    return cursor.rowcount > 0


# STEP 10: Update an existing memory

def update_memory(
    user_id,
    memory_key,
    memory_value,
    category=None,
    db_path=DATABASE_PATH
):
    validate_user_id(user_id)

    if not isinstance(memory_key, str) or not memory_key.strip():
        raise ValueError("A valid memory key is required.")

    if not isinstance(memory_value, str) or not memory_value.strip():
        raise ValueError("A valid memory value is required.")

    initialize_memory_db(db_path)

    updated_at = datetime.now(timezone.utc).isoformat()

    with database_connection(db_path) as connection:

        if category is None:
            cursor = connection.execute("""
                UPDATE user_memories
                SET memory_value = ?, updated_at = ?
                WHERE user_id = ? AND memory_key = ?
            """, (
                memory_value,
                updated_at,
                user_id,
                memory_key
            ))

        else:
            cursor = connection.execute("""
                UPDATE user_memories
                SET memory_value = ?, category = ?, updated_at = ?
                WHERE user_id = ? AND memory_key = ?
            """, (
                memory_value,
                category,
                updated_at,
                user_id,
                memory_key
            ))

    return cursor.rowcount > 0


# STEP 11: Delete all memories belonging to one user

def delete_all_user_memories(user_id, db_path=DATABASE_PATH):
    validate_user_id(user_id)
    initialize_memory_db(db_path)

    with database_connection(db_path) as connection:
        cursor = connection.execute("""
            DELETE FROM user_memories
            WHERE user_id = ?
        """, (user_id,))

    return cursor.rowcount
