from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse


def _is_admin(u):
    return u.is_authenticated and (u.is_staff or getattr(u, 'rol', '') in ('admin', 'superadmin'))


def _is_superadmin(u):
    return u.is_authenticated and (u.is_superuser or getattr(u, 'rol', '') == 'superadmin')


def admin_required(view_func):
    return login_required(user_passes_test(_is_admin)(view_func))


def superadmin_required(view_func):
    return login_required(user_passes_test(_is_superadmin)(view_func))


def ajax_only(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'AJAX only'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper
