
from app.memory.memory_store import (
    get_user_memories,
    update_memory,
    delete_memory,
    delete_all_user_memories
)


# STEP 1: Review a user's memories

def review_memories(user_id):
    return get_user_memories(user_id)


# STEP 2: Update an existing memory

def change_memory(user_id, memory_key, new_value, category=None):
    return update_memory(
        user_id,
        memory_key,
        new_value,
        category
    )


# STEP 3: Delete one memory

def remove_memory(user_id, memory_key):
    return delete_memory(user_id, memory_key)


# STEP 4: Delete all memories belonging to one user

def clear_user_memories(user_id):
    return delete_all_user_memories(user_id)
