"""Views de batch (lotes de certificados).

Solo las que tienen forms con uploads Excel / mapping / file uploads del diseño
se quedan como Django views. El resto (list, delete, preview_pdf) va por API.
"""
import base64

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Signature, CertificateBatch
from core.services.excel_service import analyze_headers, process_excel_batch
from ._shared import admin_required
from core.security.decorators import module_required


@admin_required
@module_required('lotes')
def list_batches(request):
    """Render con los lotes para el template de lista."""
    return render(request, 'panel/batch/list.html', {
        'lotes': CertificateBatch.objects.all().order_by('id'),
    })


@admin_required
@module_required('lotes', 'crear')
def create_batch(request):
    """Shell del form. Submit va a /api/v1/admin/batches/ via fetch+FormData."""
    from core.models import FACULTY_CHOICES
    return render(request, 'panel/batch/form.html', {
        'facultades_choices': FACULTY_CHOICES,
    })


@admin_required
@module_required('lotes', 'crear')
def process_batch_mapping(request, id):
    """UI de mapeo de columnas Excel tras crear el lote."""
    lote = get_object_or_404(CertificateBatch, id=id)

    if request.method == 'POST':
        name_strategy = request.POST.get('name_strategy', 'single')
        if name_strategy == 'split':
            col_nombres = request.POST.get('col_nombres_split')
            col_apellidos = request.POST.get('col_apellidos')
        else:
            col_nombres = request.POST.get('col_nombres')
            col_apellidos = None

        mapping = {
            'cedula': request.POST.get('col_cedula'),
            'nombres': col_nombres,
            'apellidos': col_apellidos,
            'email': request.POST.get('col_email'),
            'celular': request.POST.get('col_celular'),
            'curso': request.POST.get('col_curso'),
        }
        try:
            success, msg = process_excel_batch(lote.id, mapping=mapping)
            if success:
                messages.success(request, f'Lote cargado exitosamente. {msg}')
                if lote.excel_file:
                    lote.excel_file.delete(save=True)
                return redirect('panel:batch_list')
            messages.error(request, f'Error al procesar: {msg}')
        except Exception as e:
            messages.error(request, f'Error crítico: {e}')
        return redirect('panel:batch_process_mapping', id=lote.id)

    analysis = analyze_headers(lote.id)
    if not analysis['success']:
        messages.error(request, f"Error leyendo el Excel: {analysis.get('error')}")
        return redirect('panel:batch_list')

    return render(request, 'panel/batch/mapping.html', {
        'lotes': lote,
        'columns': analysis['columns'],
        'suggestions': analysis['suggestions'],
        'preview': analysis['preview'],
    })


@admin_required
@module_required('lotes')
def batch_detail(request, id):
    lote = get_object_or_404(CertificateBatch, id=id)
    return render(request, 'panel/batch/detail.html', {
        'lote': lote,
        'certificados': lote.certificates.all(),
    })


@admin_required
@module_required('lotes', 'editar')
def configure_batch(request, id):
    """Form de diseño personalizado para un lote (colores, firmas, logos)."""
    from django.urls import reverse
    from core.models.catalogs.enums import CertificateKind
    lote = get_object_or_404(CertificateBatch, id=id)

    # A dónde volver al salir/guardar el diseño:
    #  - lote de programa  → detalle del programa
    #  - lote de un seminario (tiene evento) → lista de eventos
    #  - lote suelto (Excel/manual) → detalle del lote
    if getattr(lote, 'kind', None) == CertificateKind.PROGRAM and lote.program_id:
        back_url = reverse('panel:program_detail', args=[lote.program_id])
    elif lote.events.exists():
        back_url = reverse('panel:session_list')
    else:
        back_url = reverse('panel:batch_detail', args=[lote.id])

    if request.method == 'POST':
        from core.models import GlobalDesign
        try:
            diseno_global = GlobalDesign.load()
        except Exception:
            diseno_global = None

        lote.customize_design = request.POST.get('personalizar_diseno') == 'on'
        lote.body_text = request.POST.get('cuerpo_certificado') or lote.body_text

        plantilla = request.POST.get('plantilla')
        if plantilla:
            lote.template = plantilla
            if diseno_global and plantilla != diseno_global.template:
                lote.customize_design = True

        for src, dst in (
            ('color_primario', 'color_primary'),
            ('color_secundario', 'color_secondary'),
            ('color_terciario', 'color_tertiary'),
            ('color_texto', 'color_text'),
        ):
            val = request.POST.get(src)
            if val:
                setattr(lote, dst, val)
                if diseno_global and val != getattr(diseno_global, dst, None):
                    lote.customize_design = True

        for i in range(1, 4):
            firma_id = request.POST.get(f'firma_inst_{i}')
            if firma_id:
                setattr(lote, f'signature_inst_{i}_id', int(firma_id))
            else:
                setattr(lote, f'signature_inst_{i}', None)

        lote.signature_inst_4 = None
        if (nombre := request.POST.get('nombre_firma_4')) is not None:
            lote.signature_name_4 = nombre
        if (cargo := request.POST.get('cargo_firma_4')) is not None:
            lote.signature_role_4 = cargo
        if 'imagen_firma_4' in request.FILES:
            file_obj = request.FILES['imagen_firma_4']
            lote.signature_image_4 = base64.b64encode(file_obj.read()).decode('utf-8')

        for i in (1, 2, 3):
            if f'logo_header_{i}' in request.FILES:
                setattr(lote, f'header_logo_{i}', request.FILES[f'logo_header_{i}'])

        lote.save()
        messages.success(
            request,
            'Diseño personalizado guardado para este lote.' if lote.customize_design
            else 'Lote actualizado. Está usando el Diseño Global.',
        )
        # "Guardar Cambios" (preview) se queda; "Finalizar" sale a back_url.
        if request.POST.get('preview'):
            return redirect('panel:batch_configure', id=lote.id)
        return redirect(back_url)

    return render(request, 'panel/batch/config.html', {
        'lote': lote,
        'firmas_institucionales': Signature.objects.filter(is_active=True).order_by('name'),
        'back_url': back_url,
    })
