"""Views de líderes académicos.

list / add_manual / upload_excel / process_mapping se quedan aquí (forms
con upload Excel). `remove` va por /api/v1/admin/participants/{id}/toggle_leader/.
"""
import uuid

import pandas as pd

from django.contrib import messages
from django.core.files.storage import default_storage
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from core.models import Participant
from core.services.excel_service import analyze_excel_file
from core.validators import sanitize_text
from ._shared import admin_required, _log_audit


@admin_required
def lideres_list(request):
    """Lista de líderes con búsqueda (render con context)."""
    q = request.GET.get('q', '').strip()
    qs = Participant.objects.filter(is_leader=True).order_by('-created_at')
    if q:
        qs = qs.filter(
            Q(national_id__icontains=q) | Q(email__icontains=q) |
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    return render(request, 'panel/lideres/list.html', {
        'lideres': qs,
        'total': Participant.objects.filter(is_leader=True).count(),
        'q': q,
    })


@admin_required
@require_http_methods(['POST'])
def lideres_add_manual(request):
    """Registrar un líder manualmente (form POST)."""
    cedula = request.POST.get('cedula', '').strip()
    nombres = request.POST.get('nombres', '').strip().upper()
    apellidos = request.POST.get('apellidos', '').strip().upper()
    email = request.POST.get('email', '').strip().lower()
    celular = request.POST.get('celular', '').strip()

    if not nombres or not apellidos:
        messages.error(request, 'Nombres y apellidos son obligatorios.')
        return redirect('panel:lideres_list')
    if not cedula and not email:
        messages.error(request, 'Debe proporcionar al menos cédula o correo.')
        return redirect('panel:lideres_list')

    participante = None
    if cedula:
        participante = Participant.objects.filter(national_id=cedula).first()
    if not participante and email:
        participante = Participant.objects.filter(email__iexact=email).first()

    if participante:
        if participante.is_leader:
            messages.info(request, f'{participante.first_name} {participante.last_name} ya es líder académico.')
        else:
            participante.is_leader = True
            updated = ['is_leader']
            if cedula and not participante.national_id:
                participante.national_id = cedula
                updated.append('national_id')
            if celular and not participante.phone:
                participante.phone = celular
                updated.append('phone')
            participante.save(update_fields=updated)
            messages.success(request, f'{participante.first_name} {participante.last_name} marcado como líder.')
    else:
        Participant.objects.create(
            national_id=cedula, first_name=nombres, last_name=apellidos,
            email=email, phone=celular, is_leader=True,
        )
        messages.success(request, f'Líder {nombres} {apellidos} registrado exitosamente.')

    _log_audit(request.user, 'CREATE', f'Líder: {cedula or email}')
    return redirect('panel:lideres_list')


@admin_required
@require_http_methods(['POST'])
def lideres_upload_excel(request):
    """Step 1: upload Excel → guardar temp → mostrar UI de mapping."""
    archivo = request.FILES.get('archivo')
    if not archivo:
        messages.error(request, 'No se seleccionó ningún archivo.')
        return redirect('panel:lideres_list')

    temp_path = default_storage.save(f'temp/lideres_{uuid.uuid4().hex[:8]}.xlsx', archivo)
    full_path = default_storage.path(temp_path)

    analysis = analyze_excel_file(full_path)
    if not analysis['success']:
        default_storage.delete(temp_path)
        messages.error(request, f"Error leyendo Excel: {analysis.get('error')}")
        return redirect('panel:lideres_list')

    request.session['lideres_temp_file'] = temp_path
    return render(request, 'panel/lideres/mapping.html', {
        'columns': analysis['columns'],
        'suggestions': analysis['suggestions'],
        'preview': analysis['preview'],
    })


@admin_required
@require_http_methods(['POST'])
def lideres_process_mapping(request):
    """Step 2: procesar Excel con el mapping confirmado."""
    temp_path = request.session.pop('lideres_temp_file', None)
    if not temp_path:
        messages.error(request, 'Sesión expirada. Sube el Excel de nuevo.')
        return redirect('panel:lideres_list')

    full_path = default_storage.path(temp_path)

    name_strategy = request.POST.get('name_strategy', 'single')
    col_cedula = request.POST.get('col_cedula')
    col_email = request.POST.get('col_email')
    col_celular = request.POST.get('col_celular')

    if name_strategy == 'split':
        col_nombres = request.POST.get('col_nombres_split')
        col_apellidos = request.POST.get('col_apellidos')
    else:
        col_nombres = request.POST.get('col_nombres')
        col_apellidos = None

    try:
        df = pd.read_excel(full_path, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]

        nuevos = 0
        actualizados = 0

        def cell(col):
            if not col or col not in df.columns:
                return ''
            return ''  # placeholder for type hint; actual logic per row below

        for _, row in df.iterrows():
            def v(col):
                if not col or col not in df.columns:
                    return ''
                val = sanitize_text(str(row.get(col, '') or ''))
                if val.lower() == 'nan':
                    return ''
                return val

            cedula = v(col_cedula)
            email = v(col_email).lower()
            nombre_raw = v(col_nombres)
            apellido_raw = v(col_apellidos)
            celular = v(col_celular)

            if cedula.endswith('.0'):
                cedula = cedula[:-2]

            if not cedula and not email:
                continue

            final_nombres = 'LÍDER'
            final_apellidos = 'ACADÉMICO'
            if apellido_raw:
                final_nombres = nombre_raw.upper()
                final_apellidos = apellido_raw.upper()
            elif nombre_raw:
                parts = nombre_raw.split()
                if len(parts) == 1:
                    final_nombres = nombre_raw.upper()
                elif len(parts) == 2:
                    final_nombres, final_apellidos = parts[0].upper(), parts[1].upper()
                elif len(parts) == 3:
                    final_nombres = parts[0].upper()
                    final_apellidos = f'{parts[1]} {parts[2]}'.upper()
                else:
                    mid = len(parts) // 2
                    final_nombres = ' '.join(parts[:mid]).upper()
                    final_apellidos = ' '.join(parts[mid:]).upper()

            participante = None
            if cedula:
                participante = Participant.objects.filter(national_id=cedula).first()
            if not participante and email:
                participante = Participant.objects.filter(email__iexact=email).first()

            if participante:
                changed = False
                if not participante.is_leader:
                    participante.is_leader = True
                    changed = True
                if cedula and not participante.national_id:
                    participante.national_id = cedula
                    changed = True
                if email and not participante.email:
                    participante.email = email
                    changed = True
                if final_nombres != 'LÍDER' and participante.first_name in ('', 'LÍDER', 'PARTICIPANTE'):
                    participante.first_name = final_nombres
                    changed = True
                if final_apellidos != 'ACADÉMICO' and participante.last_name in ('', 'ACADÉMICO', 'S/N'):
                    participante.last_name = final_apellidos
                    changed = True
                if celular and not participante.phone:
                    participante.phone = celular
                    changed = True
                if changed:
                    participante.save()
                    actualizados += 1
            else:
                Participant.objects.create(
                    national_id=cedula, first_name=final_nombres, last_name=final_apellidos,
                    email=email, phone=celular, is_leader=True,
                )
                nuevos += 1

        _log_audit(request.user, 'CREATE', f'Líderes Excel: {nuevos} nuevos, {actualizados} actualizados')
        messages.success(request, f'Excel procesado: {nuevos} líderes nuevos, {actualizados} actualizados.')

    except Exception as e:
        messages.error(request, f'Error procesando: {e}')
    finally:
        try:
            default_storage.delete(temp_path)
        except Exception:
            pass

    return redirect('panel:lideres_list')
