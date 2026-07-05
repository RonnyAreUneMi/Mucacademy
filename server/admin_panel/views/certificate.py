"""add_certificate: POST handler para form del batch detail.

participante_lookup eliminado: usar /api/v1/admin/participants/?search= directamente.
"""
from datetime import datetime
import uuid

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from core.models import Certificate, CertificateBatch, Participant
from ._shared import admin_required, _log_audit


@admin_required
def add_certificate(request, id):
    """POST form del batch_detail para agregar un certificado al lote."""
    lote = get_object_or_404(CertificateBatch, id=id)

    if request.method != 'POST':
        return redirect('panel:batch_detail', id=lote.id)

    try:
        fecha_str = request.POST.get('fecha_curso')
        fecha_curso = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None

        cedula_raw = (request.POST.get('cedula') or '').strip()
        nombres_raw = (request.POST.get('nombres') or '').strip().upper()
        apellidos_raw = (request.POST.get('apellidos') or '').strip().upper()
        email_raw = (request.POST.get('email') or '').strip().lower()
        celular_raw = (request.POST.get('celular') or '').strip()

        is_generated = cedula_raw.startswith('GEN-') or not cedula_raw
        real_cedula = '' if is_generated else cedula_raw

        participante = None
        if real_cedula:
            participante = Participant.objects.filter(national_id=real_cedula).first()
        if not participante and email_raw:
            participante = Participant.objects.filter(email__iexact=email_raw).first()

        if participante:
            updated = []
            if real_cedula and not participante.national_id:
                participante.national_id = real_cedula
                updated.append('national_id')
            if celular_raw and not participante.phone:
                participante.phone = celular_raw
                updated.append('phone')
            if updated:
                participante.save(update_fields=updated)
        else:
            participante = Participant.objects.create(
                national_id=real_cedula, first_name=nombres_raw, last_name=apellidos_raw,
                email=email_raw, phone=celular_raw,
            )

        Certificate.objects.create(
            batch=lote, participant=participante,
            national_id=cedula_raw or f'GEN-{uuid.uuid4().hex[:8].upper()}',
            first_name=nombres_raw, last_name=apellidos_raw, email=email_raw,
            course=request.POST.get('curso'),
            hours=int(request.POST.get('horas', 0)),
            course_date=fecha_curso,
        )
        _log_audit(
            request.user, 'CREATE',
            f'Certificado agregado manual: {cedula_raw} en lote {lote.name}',
        )
        messages.success(request, 'Certificado agregado correctamente.')
    except Exception as e:
        messages.error(request, f'Error al agregar certificado: {e}')

    return redirect('panel:batch_detail', id=lote.id)
