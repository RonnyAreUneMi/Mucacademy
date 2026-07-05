import base64
import random
import uuid
from datetime import date

from django.contrib import messages
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST

from core.models import Certificate, Signature, CertificateBatch
from core.services.pdf_service import generate_certificate_pdf
from ._shared import superadmin_required, _log_audit

@superadmin_required
def design_global(request):
    """
    Configuración GLOBAL del diseño de certificados.
    Solo el superadmin puede modificarla. Aplica a todos los lotes.
    """
    from core.models import GlobalDesign
    diseno = GlobalDesign.load()

    if request.method == 'POST':
        cuerpo = request.POST.get('cuerpo_certificado')
        if cuerpo is not None:
            diseno.body_text = cuerpo

        plantilla = request.POST.get('plantilla')
        if plantilla:
            diseno.template = plantilla

        for src, dst in (
            ('color_primario', 'color_primary'),
            ('color_secundario', 'color_secondary'),
            ('color_terciario', 'color_tertiary'),
            ('color_texto', 'color_text'),
        ):
            val = request.POST.get(src)
            if val:
                setattr(diseno, dst, val)

        # Firmas institucionales 1, 2, 3
        for i in range(1, 4):
            firma_id = request.POST.get(f'firma_inst_{i}')
            if firma_id:
                setattr(diseno, f'signature_inst_{i}_id', int(firma_id))
            else:
                setattr(diseno, f'signature_inst_{i}', None)

        # Firma personalizada (4)
        nombre = request.POST.get('nombre_firma_4')
        cargo = request.POST.get('cargo_firma_4')
        if nombre is not None:
            diseno.signature_name_4 = nombre
        if cargo is not None:
            diseno.signature_role_4 = cargo
        if 'imagen_firma_4' in request.FILES:
            file_obj = request.FILES['imagen_firma_4']
            encoded = base64.b64encode(file_obj.read()).decode('utf-8')
            diseno.signature_image_4 = encoded

        if 'logo_header_1' in request.FILES:
            diseno.header_logo_1 = request.FILES['logo_header_1']
        if 'logo_header_2' in request.FILES:
            diseno.header_logo_2 = request.FILES['logo_header_2']
        if 'logo_header_3' in request.FILES:
            diseno.header_logo_3 = request.FILES['logo_header_3']

        # Posición de firmas
        posicion = request.POST.get('posicion_firmas')
        if posicion:
            try:
                diseno.signatures_position = float(posicion)
            except (ValueError, TypeError):
                pass

        diseno.save()
        _log_audit(request.user, 'UPDATE', 'Diseño global actualizado')
        messages.success(request, 'Diseño global guardado. Aplica a todos los certificados.')
        return redirect('panel:design_global')

    firmas_institucionales = Signature.objects.filter(is_active=True).order_by('name')

    # Build signature preview data for visual editor
    firma_preview = []
    for i in range(1, 4):
        firma = getattr(diseno, f'signature_inst_{i}')
        if firma:
            firma_preview.append({
                'slot': i,
                'name': firma.name or '',
                'cargo': firma.role or '',
                'has_img': bool(firma.image),
                'offset_y': getattr(diseno, f'signature_{i}_offset_y', 0),
                'escala': getattr(diseno, f'signature_{i}_scale', 100),
            })
    # Firma 4 (custom)
    if diseno.signature_name_4:
        firma_preview.append({
            'slot': 4,
            'name': diseno.signature_name_4,
            'cargo': diseno.signature_role_4 or '',
            'has_img': bool(diseno.signature_image_4),
            'offset_y': getattr(diseno, 'signature_4_offset_y', 0),
            'escala': getattr(diseno, 'signature_4_scale', 100),
        })
    
    import json as json_mod
    return render(request, 'panel/design/config.html', {
        'diseno': diseno,
        'firmas_institucionales': firmas_institucionales,
        'firma_preview_json': json_mod.dumps(firma_preview),
    })


@superadmin_required
@require_POST
def design_save_firma_pos(request):
    """AJAX: Save per-signature position/scale from the visual editor."""
    from core.models import GlobalDesign
    import json as json_mod

    try:
        data = json_mod.loads(request.body)
    except (json_mod.JSONDecodeError, AttributeError):
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    diseno = GlobalDesign.load()

    for item in data.get('firmas', []):
        slot = item.get('slot')
        if slot not in (1, 2, 3, 4):
            continue
        offset_y = item.get('offset_y', 0)
        escala = item.get('escala', 100)
        setattr(diseno, f'signature_{slot}_offset_y', float(offset_y))
        setattr(diseno, f'signature_{slot}_scale', float(escala))

    # Also save global signatures_position if provided
    if 'posicion_firmas' in data:
        diseno.signatures_position = float(data['posicion_firmas'])
    
    diseno.save()
    return JsonResponse({'ok': True})


@superadmin_required
@xframe_options_exempt
def design_global_preview(request):
    """Preview del diseño global con datos dummy."""
    # Buscar cualquier lote para asociar el dummy_cert (necesario por FK)
    lote = CertificateBatch.objects.first()
    if not lote:
        # Crear un lote temporal en memoria (no se persiste)
        return HttpResponse("Crea primero un lote para previsualizar el diseño.", status=400)

    dummy_cert = Certificate(
        batch=lote,
        national_id="0999999999",
        first_name="ESTUDIANTE",
        last_name="DE PRUEBA",
        email="prueba@unemi.edu.ec",
        course="CURSO DE DEMOSTRACIÓN",
        course_date=date.today(),
        hours=40,
        verification_hash=uuid.uuid4(),
    )
    dummy_cert.id = random.randint(10000, 99999)

    try:
        pdf_buffer = generate_certificate_pdf(dummy_cert)
        response = FileResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="DesignPreview.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error generando preview: {str(e)}", status=500)


