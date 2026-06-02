def log_audit(user, action: str, detail: str) -> None:
    """Create an audit record. Safe if user is None or anonymous."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return
    # Lazy import to avoid circular imports with core.models
    from core.models import AuditLog
    AuditLog.objects.create(user=user, action=action, details=detail)


class AuditLogMixin:
    """Mixin for views/viewsets that record audit logs.

    Usage:
        class MyView(AuditLogMixin, APIView):
            audit_action = 'CREATE'
            audit_detail_template = 'Thing created: {obj}'
    """
    audit_action = ''
    audit_detail_template = ''

    def log_audit(self, action: str = '', detail: str = '', user=None) -> None:
        user = user or getattr(getattr(self, 'request', None), 'user', None)
        log_audit(user, action or self.audit_action, detail)
