"""Views de programas: shells HTML. La lógica (CRUD + progreso) va por API."""
from django.shortcuts import get_object_or_404, render

from core.models import Program
from ._shared import admin_required


@admin_required
def program_list(request):
    """Listado de programas (shell + API /api/v1/admin/programs/)."""
    return render(request, 'panel/programs/list.html', {})


@admin_required
def program_create(request):
    """Página completa para crear un programa (POST vía API)."""
    return render(request, 'panel/programs/create.html', {})


@admin_required
def program_detail(request, id):
    """Detalle de un programa: cursos + progreso de participantes."""
    program = get_object_or_404(Program, id=id)
    return render(request, 'panel/programs/detail.html', {'program': program})
