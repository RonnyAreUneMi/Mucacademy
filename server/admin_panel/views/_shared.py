"""Helpers compartidos entre las views del admin panel."""
from functools import wraps

from django.contrib.auth.decorators import login_required, user_passes_test

from core.models import AuditLog


def _is_admin(user):
    """True si el user tiene rol admin o superadmin."""
    return user.is_authenticated and user.role in ('admin', 'superadmin')


def _is_superadmin(user):
    """True solo para superadmin (config global)."""
    return user.is_authenticated and user.role == 'superadmin'


def admin_required(view_func):
    """Equivalente a @login_required + @user_passes_test(_is_admin)."""
    @wraps(view_func)
    @login_required
    @user_passes_test(_is_admin)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def superadmin_required(view_func):
    """Equivalente a @login_required + @user_passes_test(_is_superadmin)."""
    @wraps(view_func)
    @login_required
    @user_passes_test(_is_superadmin)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def _log_audit(user, action, detail):
    """Crea entry en Auditoria si user es autenticado."""
    if user and user.is_authenticated:
        AuditLog.objects.create(user=user, action=action, details=detail)
