"""Shells de firmas: create y edit. Toda la lógica va por /api/v1/admin/firmas/."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Signature


def _is_superadmin(user):
    return user.is_authenticated and user.role == 'superadmin'


@login_required
@user_passes_test(_is_superadmin)
def firma_create(request):
    return render(request, 'panel/firmas/form.html', {
        'title': 'Nueva Firma Institucional',
    })


@login_required
@user_passes_test(_is_superadmin)
def firma_edit(request, id):
    return render(request, 'panel/firmas/form.html', {
        'firma': get_object_or_404(Signature, id=id),
        'title': 'Editar Firma Institucional',
    })


@login_required
@user_passes_test(_is_superadmin)
def firma_delete(request, id):
    """Legacy: eliminar ahora es DELETE al API desde el template de lista."""
    return redirect('panel:firma_list')
