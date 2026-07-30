"""E2E / integración del módulo de Seguridad y el menú superior.

Pregunta que responde: si al perfil **Estudiante** le doy acciones de admin
(permisos sobre un módulo del panel), ¿se le construye ese módulo en el menú
de arriba?

Respuesta que se verifica aquí: **NO**. El menú del panel se arma con
`user_can(request.user, ...)`, que solo mapea `User.role` (admin/professor) al
perfil PROFESOR o reconoce al superadmin. El perfil 'estudiante' es exclusivo
del área pública (participantes) y nunca alimenta el menú del panel; por eso un
permiso concedido a 'estudiante' no tiene ningún efecto en el panel.
"""
import pytest
from django.test import RequestFactory

from admin_panel.context_processors import nav_menu
from core.models.catalogs.enums import AdminRole
from core.models.security import RolePermission, USER_ROLE_TO_PROFILE
from core.security import perms
from tests.factories import UserFactory, SuperAdminFactory

# Módulo crítico: superadmin-only (profesor lo tiene DENEGADO por defecto).
MOD = 'usuarios'


def _menu_modules(user):
    """Slugs de módulo que sobreviven al filtro de permisos del menú superior."""
    req = RequestFactory().get('/panel/')
    req.user = user
    groups = nav_menu(req)['nav_groups']
    mods = set()
    for g in groups:
        for item in g.get('items', []):
            if item.get('module'):
                mods.add(item['module'])
        for sec in g.get('sections', []):
            for item in sec.get('items', []):
                if item.get('module'):
                    mods.add(item['module'])
    return mods


def _grant(role, module, **flags):
    vals = {'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': True}
    vals.update(flags)
    rp, _ = RolePermission.objects.update_or_create(
        role=role, module=module, defaults=vals,
    )
    perms.invalidate_cache()
    return rp


# ─────────────────────────────────────────────────────────────────────────
# Garantías estructurales
# ─────────────────────────────────────────────────────────────────────────

def test_no_existe_rol_estudiante_en_el_panel():
    """El panel (User.role) no tiene rol 'estudiante': un student no es User de panel."""
    valores_rol_panel = {choice.value for choice in AdminRole}
    assert 'estudiante' not in valores_rol_panel
    # Y ningún User.role mapea al perfil 'estudiante'.
    assert 'estudiante' not in {str(v) for v in USER_ROLE_TO_PROFILE.values()}
    assert USER_ROLE_TO_PROFILE.get('estudiante') is None


# ─────────────────────────────────────────────────────────────────────────
# El límite de seguridad: dar permiso a 'estudiante' NO arma el módulo arriba
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_permiso_a_estudiante_no_construye_modulo_en_el_menu():
    profesor = UserFactory(role='admin')   # admin/professor → perfil PROFESOR

    # Estado base: 'usuarios' NO está en el menú del profesor (denegado por defecto).
    assert MOD not in _menu_modules(profesor)
    assert perms.user_can(profesor, MOD, 'ver') is False

    # Le damos TODAS las acciones de admin al perfil 'estudiante' sobre 'usuarios'.
    _grant('estudiante', MOD)

    # El permiso queda registrado para el perfil estudiante (lado participante)…
    assert perms.role_can('estudiante', MOD, 'ver') is True
    assert perms.participant_can(MOD, 'ver') is True

    # …pero NO cambia nada en el panel: el profesor sigue sin el módulo y el
    # menú superior NO lo construye.
    assert perms.user_can(profesor, MOD, 'ver') is False
    assert MOD not in _menu_modules(profesor)


@pytest.mark.django_db
def test_permiso_a_estudiante_no_altera_el_menu_del_profesor():
    """Aún concediendo al estudiante todo, el conjunto de módulos del profesor
    es idéntico antes y después."""
    profesor = UserFactory(role='admin')
    antes = _menu_modules(profesor)

    for m in ('usuarios', 'design_system', 'bitacora', 'modelado', 'ai_config'):
        _grant('estudiante', m)

    despues = _menu_modules(profesor)
    assert antes == despues


# ─────────────────────────────────────────────────────────────────────────
# Contraste: el menú SÍ es dirigido por permisos (revocar → desaparece)
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_el_menu_respeta_los_permisos_del_profesor():
    """Prueba de control: el filtro por permisos del menú funciona de verdad.
    'eventos' lo tiene el profesor por defecto → aparece; si se le revoca la
    vista, desaparece del menú superior."""
    profesor = UserFactory(role='admin')
    assert 'eventos' in _menu_modules(profesor)

    _grant('profesor', 'eventos', can_view=False, can_create=False,
           can_edit=False, can_delete=False)

    assert perms.user_can(profesor, 'eventos', 'ver') is False
    assert 'eventos' not in _menu_modules(profesor)


@pytest.mark.django_db
def test_superadmin_ve_el_modulo_siempre():
    """El superadmin ve el módulo crítico (grupo superadmin-only) siempre."""
    sa = SuperAdminFactory()
    assert perms.user_can(sa, MOD, 'ver') is True
    assert MOD in _menu_modules(sa)


# ─────────────────────────────────────────────────────────────────────────
# Demo en vivo: el grupo "Admin" es por permiso → si el superadmin le da a un
# docente acceso a un módulo, se le construye en el menú al instante.
# ─────────────────────────────────────────────────────────────────────────

def _menu_group_labels(user):
    req = RequestFactory().get('/panel/')
    req.user = user
    return {g['label'] for g in nav_menu(req)['nav_groups']}


@pytest.mark.django_db
def test_docente_con_permiso_ve_el_modulo_de_config():
    """El superadmin le concede al docente el módulo de Configuración IA →
    aparece en su menú (antes no estaba)."""
    docente = UserFactory(role='admin')
    assert 'ai_config' not in _menu_modules(docente)   # sin permiso: oculto

    _grant('profesor', 'ai_config', can_view=True)      # solo ver

    assert perms.user_can(docente, 'ai_config', 'ver') is True
    assert 'ai_config' in _menu_modules(docente)        # ya se le construye


@pytest.mark.django_db
def test_docente_abre_la_pagina_solo_con_permiso(client):
    """El fix de fondo: la PÁGINA (no solo el menú) respeta el permiso.
    Sin permiso → redirige al dashboard; con permiso → 200."""
    docente = UserFactory(role='admin')
    docente.set_password('x'); docente.save()
    client.force_login(docente)

    url = '/panel/design-system/componentes/'   # módulo 'design_system'

    # Sin permiso (profesor default = NONE) → rebota al dashboard.
    r1 = client.get(url)
    assert r1.status_code == 302
    assert '/panel/' in r1['Location']

    # El superadmin le concede el módulo → ahora entra (200).
    _grant('profesor', 'design_system', can_view=True)
    r2 = client.get(url)
    assert r2.status_code == 200


@pytest.mark.django_db
def test_superadmin_abre_la_pagina_siempre(client):
    sa = SuperAdminFactory()
    sa.set_password('x'); sa.save()
    client.force_login(sa)
    assert client.get('/panel/design-system/componentes/').status_code == 200


@pytest.mark.django_db
def test_docente_no_gestiona_la_pantalla_de_seguridad():
    """La asignación de permisos (grupo 'Seguridad') sigue siendo solo del
    superadmin: el docente nunca la ve, aunque reciba otros módulos."""
    docente = UserFactory(role='admin')
    _grant('profesor', 'ai_config', can_view=True)
    assert 'Seguridad' not in _menu_group_labels(docente)
    assert 'Seguridad' in _menu_group_labels(SuperAdminFactory())
