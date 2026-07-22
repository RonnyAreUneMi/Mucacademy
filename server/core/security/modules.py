"""Catálogo de módulos del sistema y permisos por defecto de cada perfil.

Los slugs de área `panel` se corresponden 1:1 con las secciones reales de
`admin_panel/urls.py` y del menú (`admin_panel/context_processors.nav_menu`).
Los de área `estudiante` con las páginas de `public/urls.py` (`/cuenta/...`).
"""

AREA_PANEL = 'panel'
AREA_STUDENT = 'estudiante'

AREA_LABELS = {
    AREA_PANEL: 'Panel administrativo',
    AREA_STUDENT: 'Área del estudiante',
}

ACTIONS = ['ver', 'crear', 'editar', 'eliminar']
ACTION_LABELS = {'ver': 'Ver', 'crear': 'Crear', 'editar': 'Editar', 'eliminar': 'Eliminar'}

MODULES = [
    {'slug': 'eventos',       'label': 'Eventos',                'area': AREA_PANEL, 'icon': 'fa-calendar-days'},
    {'slug': 'programas',     'label': 'Programas',              'area': AREA_PANEL, 'icon': 'fa-diagram-project'},
    {'slug': 'lotes',         'label': 'Lotes de certificados',  'area': AREA_PANEL, 'icon': 'fa-certificate'},
    {'slug': 'participantes', 'label': 'Participantes',          'area': AREA_PANEL, 'icon': 'fa-user-graduate'},
    {'slug': 'titulos',       'label': 'Títulos académicos',     'area': AREA_PANEL, 'icon': 'fa-graduation-cap'},
    {'slug': 'diseno',        'label': 'Diseño de certificados', 'area': AREA_PANEL, 'icon': 'fa-palette'},
    {'slug': 'firmas',        'label': 'Firmas institucionales', 'area': AREA_PANEL, 'icon': 'fa-signature'},
    {'slug': 'auditoria',     'label': 'Auditoría',              'area': AREA_PANEL, 'icon': 'fa-clipboard-list'},
    {'slug': 'usuarios',      'label': 'Usuarios',               'area': AREA_PANEL, 'icon': 'fa-users-cog'},
    {'slug': 'solicitudes',   'label': 'Solicitudes de acceso',  'area': AREA_PANEL, 'icon': 'fa-user-clock'},
    {'slug': 'design_system', 'label': 'Design System',          'area': AREA_PANEL, 'icon': 'fa-swatchbook'},
    {'slug': 'ai_config',     'label': 'Configuración IA',       'area': AREA_PANEL, 'icon': 'fa-microchip'},
    {'slug': 'google',        'label': 'Google Cloud',           'area': AREA_PANEL, 'icon': 'fa-cloud'},
    {'slug': 'bitacora',      'label': 'Bitácora del proyecto',  'area': AREA_PANEL, 'icon': 'fa-list-check'},
    {'slug': 'modelado',      'label': 'Modelado de datos',      'area': AREA_PANEL, 'icon': 'fa-database'},

    {'slug': 'mis_certificados', 'label': 'Mis certificados', 'area': AREA_STUDENT, 'icon': 'fa-certificate'},
    {'slug': 'mis_eventos',      'label': 'Mis eventos',      'area': AREA_STUDENT, 'icon': 'fa-calendar-days'},
    {'slug': 'mis_programas',    'label': 'Mis programas',    'area': AREA_STUDENT, 'icon': 'fa-diagram-project'},
    {'slug': 'evaluaciones',     'label': 'Evaluaciones',     'area': AREA_STUDENT, 'icon': 'fa-list-check'},
    {'slug': 'perfil',           'label': 'Mi perfil',        'area': AREA_STUDENT, 'icon': 'fa-user'},
]

MODULE_SLUGS = [m['slug'] for m in MODULES]
MODULE_BY_SLUG = {m['slug']: m for m in MODULES}


def modules_by_area():
    """[(area, label, [modulos])] en el orden declarado en MODULES."""
    out = []
    for area in (AREA_PANEL, AREA_STUDENT):
        items = [m for m in MODULES if m['area'] == area]
        out.append((area, AREA_LABELS[area], items))
    return out


def module_label(slug: str) -> str:
    m = MODULE_BY_SLUG.get(slug)
    return m['label'] if m else slug


_ALL = (True, True, True, True)
_NONE = (False, False, False, False)
_VIEW = (True, False, False, False)

# Permisos por defecto — replican EXACTAMENTE el comportamiento actual del
# sistema. Sirven como semilla de la migración y como fallback cuando no hay
# fila de RolePermission para (perfil, módulo).
#
# `administrador` = rol User.role 'admin'. Hoy accede a lo que protege
# `admin_required`/`IsPanelAdmin`; las pantallas con `superadmin_required`
# siguen bloqueadas por su propio decorador.
DEFAULTS = {
    'administrador': {
        'eventos': _ALL,
        'programas': _ALL,
        'lotes': _ALL,
        'participantes': _ALL,
        'titulos': _ALL,
        'diseno': _ALL,
        'firmas': _ALL,
        'auditoria': _VIEW,
        'usuarios': _NONE,
        'solicitudes': _NONE,
        'design_system': _NONE,
        'ai_config': _NONE,
        'google': _NONE,
        'bitacora': _NONE,
        'modelado': _NONE,
        'mis_certificados': _NONE,
        'mis_eventos': _NONE,
        'mis_programas': _NONE,
        'evaluaciones': _NONE,
        'perfil': _NONE,
    },
    # Hoy los profesores no entran al panel (se los redirige a "Mi estado").
    # Los estudiantes solo tienen el área pública de su cuenta.
    'estudiante': {
        **{m['slug']: _NONE for m in MODULES if m['area'] == AREA_PANEL},
        'mis_certificados': _VIEW,
        'mis_eventos': (True, True, False, False),
        'mis_programas': (True, True, False, False),
        'evaluaciones': (True, True, False, False),
        'perfil': (True, False, True, False),
    },
}


def default_flags(role: str, slug: str):
    """Tupla (ver, crear, editar, eliminar) por defecto para (perfil, módulo).

    Red de seguridad anti-bloqueo: si el módulo no está en DEFAULTS (slug nuevo
    agregado en código sin semilla) se concede el acceso propio del área.
    """
    role_defaults = DEFAULTS.get(role)
    if role_defaults is None:
        return _NONE
    flags = role_defaults.get(slug)
    if flags is not None:
        return flags
    area = MODULE_BY_SLUG.get(slug, {}).get('area')
    if role == 'administrador' and area != AREA_STUDENT:
        return _ALL
    if role == 'estudiante' and area == AREA_STUDENT:
        return _ALL
    return _NONE
