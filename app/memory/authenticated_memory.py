from app.identity.context import current_identity
from app.memory.memory_store import (
    DATABASE_PATH,
    delete_all_user_memories,
    delete_memory,
    get_memory,
    get_user_memories,
    get_user_profile,
    save_memory,
    save_user_profile,
    update_memory,
)


class AuthenticatedMemoryService:
    """Expose Phase 3 memory operations without accepting caller-selected user IDs."""

    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = DATABASE_PATH if database_path is None else database_path

    def _user_id(self):
        return current_identity().user_id

    def get_profile(self):
        return get_user_profile(self._user_id(), self.database_path)

    def save_profile(self, profile):
        save_user_profile(self._user_id(), profile, self.database_path)

    def save_memory(self, memory_key, memory_value, category="general"):
        save_memory(
            self._user_id(),
            memory_key,
            memory_value,
            category,
            self.database_path,
        )

    def get_memory(self, memory_key):
        return get_memory(self._user_id(), memory_key, self.database_path)

    def get_memories(self, category=None):
        return get_user_memories(
            self._user_id(), category, self.database_path
        )

    def update_memory(self, memory_key, memory_value, category=None):
        return update_memory(
            self._user_id(),
            memory_key,
            memory_value,
            category,
            self.database_path,
        )

    def delete_memory(self, memory_key):
        return delete_memory(
            self._user_id(), memory_key, self.database_path
        )

    def delete_all_memories(self):
        return delete_all_user_memories(
            self._user_id(), self.database_path
        )
