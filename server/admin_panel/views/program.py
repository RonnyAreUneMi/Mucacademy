"""Views de programas: shells HTML. La lógica (CRUD + progreso) va por API."""
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Program
from core.services import programs as program_service
from ._shared import admin_required
from core.security.decorators import module_required


@admin_required
@module_required('programas')
def program_list(request):
    """Listado de programas (shell + API /api/v1/admin/programs/)."""
    return render(request, 'panel/programs/list.html', {})


@admin_required
@module_required('programas', 'crear')
def program_create(request):
    """Página completa para crear un programa (POST vía API)."""
    return render(request, 'panel/programs/create.html', {})


@admin_required
@module_required('programas')
def program_detail(request, id):
    """Detalle de un programa: cursos + progreso de participantes."""
    program = get_object_or_404(Program, id=id)
    return render(request, 'panel/programs/detail.html', {'program': program})


@admin_required
@module_required('programas', 'editar')
def program_certificate_design(request, id):
    """Crea (si falta) el lote-certificado del programa y abre el diseñador con preview."""
    program = get_object_or_404(Program, id=id)
    batch = program_service.get_or_create_program_batch(program, administrator=request.user)
    return redirect('panel:batch_configure', id=batch.id)
