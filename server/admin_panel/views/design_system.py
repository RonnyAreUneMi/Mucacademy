"""Vista del Design System del admin panel.

Editor visual para los tokens (colores, fuentes, radios, sombras)
que el `:root` CSS de `panel/base.html` consume vía context processor.

Solo superadmin.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.models import UIDesignTokens
from ._shared import admin_required, _log_audit
from core.security.decorators import module_required


# Campos color (input type=color, valores #RRGGBB)
COLOR_FIELDS = (
    'color_brand', 'color_brand_dark', 'color_accent',
    'color_bg_dark', 'color_bg_light',
    'color_card_dark', 'color_card_light',
    'color_text_dark', 'color_text_light',
    'color_text_muted_dark', 'color_text_muted_light',
    'color_success', 'color_danger', 'color_warning', 'color_info',
)
# Campos texto libre (fonts, shadows)
TEXT_FIELDS = (
    'font_sans', 'font_display', 'font_mono',
    'radius_sm', 'radius_md', 'radius_lg', 'radius_xl',
    'btn_blur', 'btn_saturate',
    'shadow_card', 'shadow_card_light',
)
# Campos numéricos (float)
FLOAT_FIELDS = (
    'btn_glass_opacity_dark',
    'btn_glass_opacity_light',
)


@admin_required
@module_required('design_system')
def design_system_edit(request):
    """Pantalla del Design System. GET muestra el form; POST guarda."""
    tokens = UIDesignTokens.load()

    if request.method == 'POST':
        for f in COLOR_FIELDS + TEXT_FIELDS:
            val = request.POST.get(f)
            if val is not None and val.strip():
                setattr(tokens, f, val.strip())
        for f in FLOAT_FIELDS:
            val = request.POST.get(f)
            if val is not None and val.strip():
                try:
                    setattr(tokens, f, float(val))
                except ValueError:
                    pass
        tokens.save()
        _log_audit(request.user, 'UPDATE', 'Tokens del Design System actualizados')
        messages.success(request, 'Design System guardado. Recarga para ver los cambios aplicados.')
        return redirect('panel:design_system')

    return render(request, 'panel/design_system/edit.html', {'tokens': tokens})


@admin_required
@require_POST
@module_required('design_system', 'editar')
def design_system_reset(request):
    """Restaura todos los tokens a sus valores por defecto."""
    tokens = UIDesignTokens.load()
    tokens.reset_to_defaults()
    _log_audit(request.user, 'UPDATE', 'Design System restaurado a valores por defecto')
    messages.success(request, 'Design System restaurado a los valores por defecto.')
    return redirect('panel:design_system')
