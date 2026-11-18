from app.identity.context import current_identity

class TenantGuard:
    @staticmethod
    def user_id():
        return current_identity().user_id
    @staticmethod
    def require_user(user_id):
        trusted = current_identity().user_id
        if not isinstance(user_id, str) or user_id != trusted:
            raise PermissionError("Access to another user's resources is forbidden.")
        return trusted
    @staticmethod
    def require_owner(resource, owner_field="user_id"):
        owner = resource.get(owner_field) if isinstance(resource, dict) else getattr(resource, owner_field, None)
        if owner != current_identity().user_id:
            raise PermissionError("Resource does not belong to the authenticated user.")
        return resource
