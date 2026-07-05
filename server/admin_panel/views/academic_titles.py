"""Views del catálogo de Títulos académicos (Dr., Mg., Ing., Lic.…).

CRUD server-rendered: list + create/update/delete por POST. El abreviado se
usa luego como opción en el formulario de ponentes.
"""
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.models import AcademicTitle

from ._shared import admin_required, _log_audit


def _parse_form(request):
    """Extrae y normaliza los campos del form de título académico."""
    abbreviation = request.POST.get('abbreviation', '').strip()
    name = request.POST.get('name', '').strip()
    sort_order_raw = request.POST.get('sort_order', '0').strip()
    is_active = request.POST.get('is_active') in ('on', 'true', '1', 'True')

    try:
        sort_order = max(0, int(float(sort_order_raw or 0)))
    except (TypeError, ValueError):
        sort_order = 0

    return {
        'abbreviation': abbreviation,
        'name': name,
        'sort_order': sort_order,
        'is_active': is_active,
    }


@admin_required
def titulos_list(request):
    """Lista del catálogo con búsqueda."""
    q = request.GET.get('q', '').strip()
    qs = AcademicTitle.objects.all()
    if q:
        qs = qs.filter(Q(abbreviation__icontains=q) | Q(name__icontains=q))

    titulos = list(qs)
    titulos_json = {
        t.id: {
            'abbreviation': t.abbreviation,
            'name': t.name,
            'sort_order': t.sort_order,
            'is_active': t.is_active,
        }
        for t in titulos
    }

    return render(request, 'panel/titulos/list.html', {
        'titulos': titulos,
        'titulos_json': titulos_json,
        'total': AcademicTitle.objects.count(),
        'q': q,
    })


@admin_required
@require_http_methods(['POST'])
def titulos_create(request):
    """Crear un nuevo título académico."""
    data = _parse_form(request)
    if not data['abbreviation'] or not data['name']:
        messages.error(request, 'El abreviado y el nombre son obligatorios.')
        return redirect('panel:titulos_list')

    try:
        AcademicTitle.objects.create(**data)
    except IntegrityError:
        messages.error(request, f'Ya existe un título con el abreviado "{data["abbreviation"]}".')
        return redirect('panel:titulos_list')

    _log_audit(request.user, 'CREATE', f'Título académico: {data["abbreviation"]}')
    messages.success(request, f'Título "{data["abbreviation"]}" creado.')
    return redirect('panel:titulos_list')


@admin_required
@require_http_methods(['POST'])
def titulos_update(request, id):
    """Editar un título académico existente."""
    titulo = get_object_or_404(AcademicTitle, id=id)
    data = _parse_form(request)
    if not data['abbreviation'] or not data['name']:
        messages.error(request, 'El abreviado y el nombre son obligatorios.')
        return redirect('panel:titulos_list')

    titulo.abbreviation = data['abbreviation']
    titulo.name = data['name']
    titulo.sort_order = data['sort_order']
    titulo.is_active = data['is_active']
    try:
        titulo.save()
    except IntegrityError:
        messages.error(request, f'Ya existe un título con el abreviado "{data["abbreviation"]}".')
        return redirect('panel:titulos_list')

    _log_audit(request.user, 'UPDATE', f'Título académico: {titulo.abbreviation}')
    messages.success(request, f'Título "{titulo.abbreviation}" actualizado.')
    return redirect('panel:titulos_list')


@admin_required
@require_http_methods(['POST'])
def titulos_delete(request, id):
    """Eliminar un título académico del catálogo."""
    titulo = get_object_or_404(AcademicTitle, id=id)
    abbr = titulo.abbreviation
    titulo.delete()
    _log_audit(request.user, 'DELETE', f'Título académico: {abbr}')
    messages.success(request, f'Título "{abbr}" eliminado.')
    return redirect('panel:titulos_list')
