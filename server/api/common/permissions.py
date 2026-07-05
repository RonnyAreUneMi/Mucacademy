from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Acceso de escritura solo para staff; lectura pública."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsOwnerOrAdmin(permissions.BasePermission):
    """El objeto solo puede ser leído/modificado por su dueño o por staff."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        owner_email = getattr(obj, 'email', '') or ''
        return owner_email.lower() == (user.email or '').lower()
