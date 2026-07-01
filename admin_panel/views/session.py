"""Views de sesión: shells HTML. Toda la lógica (CRUD + forms) va por API.

- list: render con context (filtros server-side para permitir ?fecha= ?estado=)
- edit: shell + fetch PATCH
- create: modal en list.html con fetch POST
- qr_display: shell + fetch a qr-info y attendees
- generate_batch: shell + fetch POST a generate-batch action
"""
from django.contrib import messages
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AcademicTitle, Enrollment, CertificateBatch, Event
from ._shared import admin_required


def _active_titles():
    """Abreviados de títulos académicos activos para el form de ponentes."""
    return list(
        AcademicTitle.objects.filter(is_active=True).values_list('abbreviation', flat=True)
    )


import re


def _series_base_name(title):
    """Quita un sufijo '(Parte N)' / 'Parte N' del título para obtener la base."""
    return re.sub(r'\s*[\(\-–]?\s*[Pp]arte\s+\d+\s*\)?\s*$', '', title or '').strip()


def _series_events(exclude_id=None):
    """Catálogo de 'primeras partes' (series) para elegir continuaciones."""
    qs = (
        Event.objects.filter(has_parts=True, parent_event__isnull=True)
        .order_by('-date').prefetch_related('parts')
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    out = []
    for e in qs:
        base = _series_base_name(e.title) or (e.title or '(sin título)')
        out.append({
            'id': e.id,
            'label': f'{e.title or "(sin título)"} · {e.date:%d/%m/%Y}',
            'base': base,
            # root es Parte 1; las continuaciones existentes suman → siguiente parte.
            'next_part': e.parts.count() + 2,
        })
    return out


@admin_required
def session_list(request):
    """Lista con filtros (el template renderiza cards server-side).

    Mutaciones (toggle/delete/create/edit) van por /api/v1/admin/sessions/.
    """
    fecha_filter = request.GET.get('fecha', '')
    estado_filter = request.GET.get('estado', '')

    qs = Event.objects.select_related('batch').annotate(
        enrolled_total=Count('enrollments'),
        attendees_total=Count('attendances'),
    )
    if fecha_filter:
        qs = qs.filter(date=fecha_filter)
    if estado_filter == 'llenas':
        qs = qs.filter(enrolled_total__gte=F('capacity'))
    elif estado_filter == 'con_registro':
        qs = qs.filter(attendees_total__gt=0)
    elif estado_filter == 'sin_registro':
        qs = qs.filter(attendees_total=0)

    return render(request, 'panel/sessions/list.html', {
        'sesiones': qs.order_by('-date', '-start_time'),
        'lotes': CertificateBatch.objects.filter(is_active=True).order_by('name'),
        'fechas_disponibles': Event.objects.dates('date', 'day', order='DESC'),
        'fecha_filter': fecha_filter,
        'estado_filter': estado_filter,
    })


@admin_required
def session_create(request):
    """Shell de creación de sesión (form completo con ponentes).

    El submit hace POST a /api/v1/admin/sessions/ vía fetch (igual que edit).
    """
    return render(request, 'panel/sessions/create.html', {
        'titulos': _active_titles(),
        'series_events': _series_events(),
    })


@admin_required
def session_edit(request, id):
    """Shell de edición: el submit va a PATCH /api/v1/admin/sessions/{id}/."""
    sesion = get_object_or_404(Event, id=id)
    ponentes = list(sesion.speakers.values('name', 'title', 'affiliation', 'bio'))
    return render(request, 'panel/sessions/edit.html', {
        'sesion': sesion,
        'ponentes_json': ponentes,
        'titulos': _active_titles(),
        'series_events': _series_events(exclude_id=sesion.id),
    })


@admin_required
def session_qr_display(request, id):
    """Pantalla de QR: muestra el código que apunta a /checkin/<codigo_qr>/.

    El template usa qrcodejs (cliente) para renderizarlo. El feed en vivo se
    consulta vía /api/v1/admin/sessions/<id>/attendees/.
    """
    sesion = get_object_or_404(Event, id=id)
    checkin_url = request.build_absolute_uri(
        f'/checkin/{sesion.qr_code}/'
    )
    total_registros = sesion.attendances.count()
    return render(request, 'panel/sessions/qr.html', {
        'sesion':           sesion,
        'checkin_url':      checkin_url,
        'total_registros':  total_registros,
    })


@admin_required
def session_generate_batch(request, id):
    """Shell para confirmar. El click del botón POSTea a /api/v1/admin/sessions/{id}/generate-batch/."""
    sesion = get_object_or_404(Event, id=id)
    if sesion.batch:
        messages.warning(request, 'Esta sesión ya tiene un lote asociado.')
        return redirect('panel:batch_configure', id=sesion.batch.id)

    total = Enrollment.objects.filter(
        event=sesion, confirmed=True, participant__isnull=False,
    ).count()
    if total == 0:
        messages.error(request, 'No hay participantes confirmados para generar certificados.')
        return redirect('panel:session_list')

    return render(request, 'panel/sessions/generate_batch.html', {
        'sesion': sesion,
        'total_confirmados': total,
    })
