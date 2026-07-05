# ADR-003 · Auth dual (Sesión Django + JWT + Sesión Participante)

- **Estado**: Aceptado
- **Fecha**: 2026-04-22

## Contexto

El sistema tiene **3 audiencias distintas**:

1. **Administradores** (admin / superadmin) — usan el panel HTML, navegación
   server-side, formularios, descargas de PDF.
2. **Clientes API externos** (futuras integraciones, mobile apps, scripts
   de admin batch) — necesitan auth stateless.
3. **Participantes públicos** — pueden usar la app sin cuenta (flujo guest
   por cédula) **o** crear cuenta con email + password / Google Sign-In.

Forzar a las 3 audiencias por el mismo mecanismo es subóptimo:

- JWT puro rompe el flujo de admin (cookies + redirects + CSRF de templates).
- Sesión Django pura no sirve para clientes API stateless.
- Usar `auth.User` para participantes obliga a crear un User por cada
  guest que se registra a un evento — explosión de usuarios "fantasma".

## Decisión

Implementamos **3 mecanismos de auth simultáneos**, cada uno para su caso:

| Mecanismo | Para quién | Cómo |
|---|---|---|
| **Sesión Django** | Admin/superadmin del panel | `auth.User` + `SessionMiddleware` |
| **JWT (`simplejwt`)** | Clientes API stateless | `Authorization: Bearer <token>` |
| **Sesión propia de Participante** | Cuenta pública | `request.session['participante_id']` |

DRF acepta los primeros dos vía:

```python
'DEFAULT_AUTHENTICATION_CLASSES': (
    'rest_framework_simplejwt.authentication.JWTAuthentication',
    'rest_framework.authentication.SessionAuthentication',
)
```

El tercero usa **el mismo session store de Django** pero un decorator
custom (`public.services.auth.login_required`) que mira `participante_id`
en lugar de `request.user`.

## Consecuencias

### Positivas

- **Cada audiencia ve sólo el mecanismo que le corresponde**.
- El flujo guest sobrevive: un participante puede inscribirse a un evento
  por cédula sin cuenta, y luego "upgradear" creando cuenta (los datos
  ya existen, sólo se le añade `password_hash`).
- **Sin tabla de usuarios fantasma**: `auth.User` queda limitado a admins.
  Los participantes (~thousands) viven en su propio modelo `Participante`
  con su propio session_id.
- Google Sign-In se monta sobre el flujo de Participante sin tocar el de admin.

### Negativas

- **Mayor complejidad mental**: hay que recordar qué decorator usar dónde
  (`@admin_required`, `@superadmin_required`, `@account_auth.login_required`,
  `@permission_classes([IsAuthenticated])`).
- **CSRF tricks**: el form de admin usa `{% csrf_token %}`, las views API
  usan `X-CSRFToken` header en fetch, los flujos de OAuth necesitan
  `csrf_exempt` en el callback.
- **Tests deben crear contexts diferentes** según la audiencia.

### Mitigaciones

- Decorators centralizados en `admin_panel/views/_shared.py` y
  `public/services/auth.py` — un solo lugar para la lógica.
- Tests de auth en `tests/test_critical_flows.py` cubren los 3 caminos.
