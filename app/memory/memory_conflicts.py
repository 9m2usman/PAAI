
from app.memory.memory_store import get_memory


# STEP 1: Compare a proposed memory with an existing memory

def detect_memory_conflict(user_id, memory):

    if not isinstance(memory, dict):
        raise ValueError("Memory must be a dictionary.")

    required_fields = {"key", "value", "category"}

    if set(memory.keys()) != required_fields:
        raise ValueError("Invalid memory structure.")

    for field in required_fields:
        if not isinstance(memory[field], str) or not memory[field].strip():
            raise ValueError("Memory fields cannot be empty.")

    existing_memory = get_memory(
        user_id,
        memory["key"]
    )

    if existing_memory is None:
        return {
            "conflict": False,
            "reason": "No existing memory",
            "existing": None,
            "proposed": memory
        }

    if existing_memory["value"].strip().lower() == memory["value"].strip().lower():
        return {
            "conflict": False,
            "reason": "Memory already contains this value",
            "existing": existing_memory,
            "proposed": memory
        }

    return {
        "conflict": True,
        "reason": "Existing memory has a different value",
        "existing": existing_memory,
        "proposed": memory
    }


# STEP 2: Resolve a conflict only after explicit approval

def resolve_memory_conflict(user_id, conflict, approved):

    if not isinstance(approved, bool):
        raise ValueError("Approval must be a boolean.")

    if not isinstance(conflict, dict):
        raise ValueError("Invalid conflict data.")

    if not conflict.get("conflict"):
        raise ValueError("There is no memory conflict to resolve.")

    if not approved:
        return {
            "updated": False,
            "message": "Existing memory was preserved."
        }

    proposed = conflict.get("proposed")

    if not isinstance(proposed, dict):
        raise ValueError("Proposed memory is missing.")

    # Recheck current database value before updating.
    current = get_memory(user_id, proposed["key"])

    if current is None:
        return {
            "updated": False,
            "message": "Existing memory no longer exists."
        }

    if current["value"] != conflict["existing"]["value"]:
        return {
            "updated": False,
            "message": "Memory changed since conflict detection. Review again."
        }

    from app.memory.memory_store import update_memory

    updated = update_memory(
        user_id,
        proposed["key"],
        proposed["value"],
        proposed["category"]
    )

    return {
        "updated": updated,
        "message": "Memory updated after approval."
    }
