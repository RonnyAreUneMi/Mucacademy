"""Shell HTML para la pantalla de configuración IA.

El form hace fetch a `/api/v1/admin/ai/config/` (PUT) y al endpoint
`/api/v1/admin/ai/config/test/` (POST) para probar la conexión.
Solo accesible para superadmins.
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from core.models import AIConfig

from ._shared import _is_admin
from core.security.decorators import module_required


@login_required
@user_passes_test(_is_admin)
@module_required('ai_config')
def ai_config(request):
    """Shell de la config IA. Los datos (proveedores + prompts) los trae el JS
    desde /api/v1/admin/ai/providers/ y /prompts/."""
    AIConfig.objects.get_or_create(pk=1)
    return render(request, 'panel/ai/config.html', {})
