from app.tenancy.tenant_guard import TenantGuard

class AuthorizationService:
    def __init__(self, permission_manager):
        self.permission_manager = permission_manager
    def require(self, integration, action):
        uid = TenantGuard.user_id()
        if not self.permission_manager.is_allowed(uid, integration, action):
            raise PermissionError("The authenticated user has not granted this permission.")
        return True
    def grant(self, integration, actions):
        self.permission_manager.grant_permission(TenantGuard.user_id(), integration, actions)
    def revoke(self, integration, action):
        return self.permission_manager.revoke_permission(TenantGuard.user_id(), integration, action)
    def list_permissions(self):
        return self.permission_manager.list_permissions(TenantGuard.user_id())
    def grant_automatic(self, integration, action):
        self.require(integration, action)
        self.permission_manager.grant_automatic_permission(TenantGuard.user_id(), integration, action)
    def is_automatic_allowed(self, integration, action):
        return self.permission_manager.is_automatic_allowed(TenantGuard.user_id(), integration, action)
