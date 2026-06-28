"""Context processors del panel admin.

`solicitudes_pendientes` — contador para badge en el menú.
`nav_menu` — estructura completa del menú principal (desktop + mobile).
`design_tokens` — tokens del Design System (singleton) para inyectar en :root CSS.
"""
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse, NoReverseMatch

from core.models import AccessRequest, UIDesignTokens


def solicitudes_pendientes(request):
    if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role == 'superadmin':
        pendientes_count = AccessRequest.objects.filter(status='pending').count()
        return {'pendientes_count': pendientes_count}
    return {'pendientes_count': 0}


def design_tokens(request):
    """Inyecta el singleton UIDesignTokens en todos los templates del panel.

    El template lo consume vía `{{ design.color_brand }}`, etc., dentro
    del `<style>` del :root para producir las CSS custom properties.

    Tolera estado de DB no migrada devolviendo `None`, y el template
    cae a defaults hardcodeados.
    """
    try:
        return {'design': UIDesignTokens.load()}
    except (OperationalError, ProgrammingError):
        return {'design': None}


def _safe_url(name: str) -> str:
    """reverse() que devuelve '#' si el nombre no existe (evita crashear el nav)."""
    try:
        return reverse(name)
    except NoReverseMatch:
        return '#'


def nav_menu(request):
    """Estructura del menú principal en data — usada por base.html.

    Formato:
        groups = [
            {
                'label': str,
                'icon': str (FA class),
                'match_keywords': [str],   # para resaltar el tab activo según url_name
                'visible': bool,           # filtro por rol
                'items': [
                    {'label', 'icon', 'url', 'badge'? (key del context)}, ...
                ],
            }
        ]
    """
    if not request.user.is_authenticated:
        return {'nav_groups': []}

    is_superadmin = (
        hasattr(request.user, 'role') and request.user.role == 'superadmin'
    )

    # Paleta DS: brand · accent · success · info · warning · danger
    # Regla: ningún color consecutivo dentro de un mismo grupo.
    groups = [
        {
            'label': 'Certificados',
            'icon': 'fa-certificate',
            'match_keywords': ['batch'],
            'visible': True,
            'items': [
                {'label': 'Ver lotes',   'icon': 'fa-list-ul', 'url': _safe_url('panel:batch_list'),   'color': 'info'},
                {'label': 'Subir nuevo', 'icon': 'fa-plus',    'url': _safe_url('panel:batch_create'), 'color': 'brand'},
            ],
        },
        {
            'label': 'Gestión',
            'icon': 'fa-users-gear',
            'match_keywords': ['session', 'participantes'],
            'visible': True,
            'items': [
                {'label': 'Eventos',       'icon': 'fa-calendar-days',   'url': _safe_url('panel:session_list'),        'color': 'success'},
                # Líderes: sección deshabilitada (oculta del menú).
                {'label': 'Participantes', 'icon': 'fa-user-graduate',   'url': _safe_url('panel:participantes_list'),  'color': 'info'},
            ],
        },
        {
            'label': 'Admin',
            'icon': 'fa-gears',
            'match_keywords': ['solicitudes', 'firma', 'design', 'ai_config', 'usuarios', 'titulos'],
            'visible': is_superadmin,
            'items': [
                {'label': 'Solicitudes',      'icon': 'fa-user-clock',     'url': _safe_url('panel:solicitudes_pendientes'), 'badge': 'pendientes_count', 'color': 'warning'},
                {'label': 'Títulos académicos','icon': 'fa-user-graduate', 'url': _safe_url('panel:titulos_list'),           'color': 'info'},
                {'label': 'Firmas inst.',     'icon': 'fa-signature',   'url': _safe_url('panel:firma_list'),             'color': 'accent'},
                {'label': 'Diseño global',    'icon': 'fa-palette',     'url': _safe_url('panel:design_global'),          'color': 'success'},
                {'label': 'Design System',    'icon': 'fa-swatchbook',  'url': _safe_url('panel:design_system'),          'color': 'brand',  'highlight': True},
                {'label': 'Configuración IA', 'icon': 'fa-microchip',   'url': _safe_url('panel:ai_config'),              'color': 'danger', 'highlight': True},
                {'label': 'Usuarios',         'icon': 'fa-users-cog',   'url': _safe_url('panel:usuarios_list'),          'color': 'info'},
            ],
        },
    ]

    return {'nav_groups': [g for g in groups if g['visible']]}
