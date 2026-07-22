"""Decoradores de bloqueo por módulo para vistas del panel y del estudiante."""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .perms import participant_can, user_can

DENIED_MESSAGE = 'No tienes permiso para acceder a este módulo.'


def module_required(module: str, action: str = 'ver'):
    """Bloquea una vista del panel si el rol del usuario no tiene el permiso."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            if user is not None and user.is_authenticated and not user_can(user, module, action):
                messages.error(request, DENIED_MESSAGE)
                return redirect('panel:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def student_module_required(module: str, action: str = 'ver'):
    """Bloquea una página del área de estudiante según el perfil `estudiante`."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not participant_can(module, action):
                messages.error(request, DENIED_MESSAGE)
                return redirect('public:account_dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
