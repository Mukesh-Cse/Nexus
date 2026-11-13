from dataclasses import dataclass
@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    authenticated: bool = False

def require_tenant(context, tenant_id):
    if not context or not context.authenticated or context.tenant_id != tenant_id:
        raise PermissionError("Access denied to private company information")

