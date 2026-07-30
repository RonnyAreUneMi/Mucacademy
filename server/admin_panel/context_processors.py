"""Context processors del panel admin.

`solicitudes_pendientes` — contador para badge en el menú.
`nav_menu` — estructura completa del menú principal (desktop + mobile).
`design_tokens` — tokens del Design System (singleton) para inyectar en :root CSS.
"""
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe

from core.models import AccessRequest, UIDesignTokens
from core.security.modules import ACTIONS, MODULES
from core.security.perms import user_can


# Logo Google (4 colores) inline, dimensionado para el disco del nav.
GOOGLE_SVG = mark_safe(
    '<svg viewBox="-3 0 262 262" width="17" height="17" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M255.878 133.451c0-10.734-.871-18.567-2.756-26.69H130.55v48.448h71.947c-1.45 12.04-9.283 30.172-26.69 42.356l-.244 1.622 38.755 30.023 2.685.268c24.659-22.774 38.875-56.282 38.875-96.027" fill="#4285F4"/>'
    '<path d="M130.55 261.1c35.248 0 64.839-11.605 86.453-31.622l-41.196-31.913c-11.024 7.688-25.82 13.055-45.257 13.055-34.523 0-63.824-22.773-74.269-54.25l-1.531.13-40.298 31.187-.527 1.465C35.393 231.798 79.49 261.1 130.55 261.1" fill="#34A853"/>'
    '<path d="M56.281 156.37c-2.756-8.123-4.351-16.827-4.351-25.82 0-8.994 1.595-17.697 4.206-25.82l-.073-1.73L15.26 71.312l-1.335.635C5.077 89.644 0 109.517 0 130.55s5.077 40.905 13.925 58.602l42.356-32.782" fill="#FBBC05"/>'
    '<path d="M130.55 50.479c24.514 0 41.05 10.589 50.479 19.438l36.844-35.974C195.245 12.91 165.798 0 130.55 0 79.49 0 35.393 29.301 13.925 71.947l42.211 32.783c10.59-31.477 39.891-54.251 74.414-54.251" fill="#EB4335"/>'
    '</svg>'
)


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
            'color': '#F58830',
            'match_keywords': ['batch'],
            'visible': True,
            'items': [
                {'label': 'Ver lotes',   'icon': 'fa-list-ul', 'url': _safe_url('panel:batch_list'),   'color': 'info', 'module': 'lotes'},
                {'label': 'Subir nuevo', 'icon': 'fa-plus',    'url': _safe_url('panel:batch_create'), 'color': 'brand', 'module': 'lotes'},
            ],
        },
        {
            'label': 'Gestión',
            'icon': 'fa-users-gear',
            'color': '#0EA5E9',
            'match_keywords': ['session', 'participantes', 'program'],
            'visible': True,
            'items': [
                {'label': 'Eventos',       'icon': 'fa-calendar-days',   'url': _safe_url('panel:session_list'),        'color': 'success', 'module': 'eventos'},
                {'label': 'Programas',     'icon': 'fa-diagram-project', 'url': _safe_url('panel:program_list'),        'color': 'brand', 'module': 'programas'},
                # Líderes: sección deshabilitada (oculta del menú).
                {'label': 'Participantes', 'icon': 'fa-user-graduate',   'url': _safe_url('panel:participantes_list'),  'color': 'info', 'module': 'participantes'},
            ],
        },
        {
            'label': 'Seguridad',
            'icon': 'fa-shield-halved',
            'color': '#EF4444',
            'match_keywords': ['seguridad'],
            'visible': is_superadmin,
            'items': [
                {'label': 'Permisos por perfil', 'icon': 'fa-user-shield', 'url': _safe_url('panel:seguridad'), 'color': 'danger'},
            ],
        },
        {
            'label': 'Admin',
            'icon': 'fa-gears',
            'color': '#8B5CF6',
            'match_keywords': ['solicitudes', 'firma', 'design', 'ai_config', 'usuarios', 'titulos', 'google', 'modelado'],
            # Visible por PERMISO (no solo superadmin): cada item se filtra por
            # user_can, y el grupo aparece solo si el usuario tiene al menos uno.
            # Así, si el superadmin le da a un docente acceso (p. ej. Configuración),
            # ese módulo se le construye en el menú al instante.
            'visible': True,
            'sections': [
                {
                    'title': 'Configuración',
                    'icon': 'fa-sliders',
                    'items': [
                        {'label': 'Configuración IA', 'icon': 'fa-microchip', 'url': _safe_url('panel:ai_config'),    'color': 'danger', 'module': 'ai_config'},
                        {'label': 'Google Cloud',     'svg': GOOGLE_SVG,      'url': _safe_url('panel:google_config'), 'color': 'accent', 'module': 'google'},
                        {'label': 'Firmas inst.',     'icon': 'fa-signature', 'url': _safe_url('panel:firma_list'),    'color': 'info', 'module': 'firmas'},
                    ],
                },
                {
                    'title': 'Certificados y cuentas',
                    'icon': 'fa-certificate',
                    'items': [
                        {'label': 'Diseño de certificados', 'icon': 'fa-palette',    'url': _safe_url('panel:design_global'),           'color': 'success', 'module': 'diseno'},
                        {'label': 'Solicitudes',            'icon': 'fa-user-clock', 'url': _safe_url('panel:solicitudes_pendientes'),  'badge': 'pendientes_count', 'color': 'warning', 'module': 'solicitudes'},
                        {'label': 'Docentes',               'icon': 'fa-users-cog',  'url': _safe_url('panel:usuarios_list'),           'color': 'info', 'module': 'usuarios'},
                    ],
                },
                {
                    'title': 'Sistema',
                    'icon': 'fa-database',
                    'items': [
                        {'label': 'Design System',      'icon': 'fa-swatchbook',      'url': _safe_url('panel:design_system'),  'color': 'brand', 'module': 'design_system'},
                        {'label': 'Bitácora del proyecto', 'icon': 'fa-list-check',   'url': _safe_url('panel:bitacora'),       'color': 'success', 'module': 'bitacora'},
                        {'label': 'Títulos académicos', 'icon': 'fa-user-graduate',   'url': _safe_url('panel:titulos_list'),   'color': 'accent', 'module': 'titulos'},
                        {'label': 'Modelado de datos',  'icon': 'fa-diagram-project', 'url': _safe_url('panel:modelado_datos'), 'color': 'info', 'module': 'modelado'},
                    ],
                },
            ],
        },
    ]

    return {'nav_groups': _filter_by_permissions(groups, request.user)}


def _filter_by_permissions(groups, user):
    """Quita del menú los items cuyo módulo el usuario no puede ver.

    Un item sin `module` no se filtra (ya está cubierto por `visible`).
    Grupos/secciones que quedan sin items desaparecen.
    """
    visibles = []
    for group in groups:
        if not group['visible']:
            continue
        g = dict(group)
        if 'items' in g:
            g['items'] = [i for i in g['items'] if _item_allowed(i, user)]
            if not g['items']:
                continue
        if 'sections' in g:
            secciones = []
            for sec in g['sections']:
                s = dict(sec)
                s['items'] = [i for i in s['items'] if _item_allowed(i, user)]
                if s['items']:
                    secciones.append(s)
            if not secciones:
                continue
            g['sections'] = secciones
        visibles.append(g)
    return visibles


def _item_allowed(item, user) -> bool:
    module = item.get('module')
    return True if not module else user_can(user, module, 'ver')


def module_perms(request):
    """`{{ module_perms.eventos.crear }}` — permisos del usuario para los templates."""
    if not request.user.is_authenticated:
        return {'module_perms': {}}
    return {'module_perms': {
        m['slug']: {a: user_can(request.user, m['slug'], a) for a in ACTIONS}
        for m in MODULES
    }}
