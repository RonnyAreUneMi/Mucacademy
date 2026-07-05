# Arquitectura — CertifAI

Monolito modular Django 5.2 + DRF 3.17 con **API-first** para consumo web y
móvil (Expo futuro). Orientado a tesis de grado y deploy en Railway.

## Diagrama de capas

```
┌──────────────────────────────────────────────────────────────┐
│                     CLIENTES                                  │
│  Browser admin  │  Browser público  │  Móvil Expo (futuro)   │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   PRESENTACIÓN                                │
│  admin_panel/templates  │  public/templates  │  api/ (DRF)   │
│  (shells HTML + JS)     │  (shells HTML+JS)  │  (JSON)       │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                     SERVICIOS                                 │
│  pdf/ (Strategy) │ excel/ │ email/ │ ai/ (Copilot, Voice...)│
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                      DOMINIO                                  │
│  models.py │ base/ (ABC, mixins) │ managers/ (QS) │ validators│
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   INFRAESTRUCTURA                             │
│   PostgreSQL (prod) / SQLite (dev)  │  Railway   │  Sentry  │
└──────────────────────────────────────────────────────────────┘
```

## Estructura de carpetas

```
certifai/
├── api/                      ← API REST (DRF)
│   ├── common/               ← AuditedModelViewSet, permisos, paginación
│   ├── auth/                 ← JWT login/refresh/me (compartido)
│   ├── admin/                ← 🔒 Recursos auth-required (12 dominios)
│   │   ├── dashboard/
│   │   ├── sessions/
│   │   ├── batches/
│   │   ├── certificates/
│   │   ├── participants/
│   │   ├── users/
│   │   ├── firmas/
│   │   ├── design/
│   │   ├── landing/
│   │   ├── audit/
│   │   └── ai/               ← placeholders (fase 8-12)
│   └── public/               ← 🌐 Read-only + inscripción
│       ├── stats/
│       ├── sessions/
│       ├── certificates/
│       ├── attendance/
│       ├── checkin/
│       └── verify/
│
├── core/                     ← Dominio + servicios
│   ├── models.py             ← Entidades (569 LOC)
│   ├── base/                 ← Abstracciones (TimestampedModel, SingletonModel, AuditLogMixin)
│   ├── managers/             ← 4 managers custom con QuerySets encadenables
│   └── services/
│       ├── pdf/              ← ⚡ Strategy pattern (9 archivos modulares)
│       │   ├── generator.py  ← orchestrator
│       │   └── designs/      ← classic, modern, geometric + DESIGN_REGISTRY
│       ├── excel/
│       ├── email/
│       └── ai/               ← scaffold para Fase 8-12
│
├── admin_panel/              ← UI admin (Django MVC) — mayormente shells
│   ├── views/                ← Solo forms con uploads (Excel, PDF, logos)
│   └── templates/panel/      ← HTML que consume /api/v1/admin/
│
├── public/                   ← UI pública
│   ├── urls.py               ← TemplateView + RedirectView (sin views.py)
│   └── templates/public/     ← HTML que consume /api/v1/public/
│
├── config/                   ← settings.py (env-driven) + urls.py raíz
├── tests/                    ← pytest + factory-boy (30+ tests)
└── docs/                     ← esta documentación
```

## Patrones arquitectónicos aplicados

### 1. Strategy — PDF generation

```
core/services/pdf/designs/__init__.py
  DESIGN_REGISTRY = {'clasico': draw_classic_wow, 'moderno': ..., 'geometrico': ...}
  get_design(plantilla) → función correspondiente
```

Para agregar una plantilla nueva basta con:
1. Crear `designs/<nombre>.py` con una función `draw_<nombre>_wow(c, cert, w, h, pri, sec, ter, txt)`
2. Registrarla en `designs/__init__.py`

Zero modificaciones al orchestrator. **Open/Closed principle**.

### 2. Template Method — AuditedModelViewSet

```python
class AuditedModelViewSet(AuditLogMixin, ModelViewSet):
    audit_verbose_name = 'recurso'

    def perform_create(self, serializer):
        instance = serializer.save()
        self.log_audit(self._action_code('create'), self.audit_detail(instance, 'create'))
    # idem update, destroy

    def audit_detail(self, instance, action) → str:
        """Subclasses override for richer messages."""
```

Cada ViewSet concreta solo define `audit_verbose_name` y opcionalmente override
`audit_detail`. La auditoría es automática en **todas** las operaciones de escritura.

### 3. Repository — Custom Managers + QuerySets

```python
Certificado.objects.search(q).with_relations().downloaded()
Sesion.objects.upcoming().with_stats()
Participante.objects.lideres()
```

Lógica de queries **encapsulada en el modelo**, no duplicada en views.

### 4. Separation of Concerns — Shell vs. Lógica

- **`admin_panel/urls.py`**: TemplateView + RedirectView para páginas puramente
  declarativas. Auth decorator inline.
- **`admin_panel/views/`**: Solo lógica real (forms con validación, uploads Excel,
  PDF generation server-side).
- **`public/urls.py`**: 100% TemplateView. Cero Python de aplicación.

### 5. Dual authentication — Session + JWT

```python
REST_FRAMEWORK = {
  'DEFAULT_AUTHENTICATION_CLASSES': (
    'rest_framework_simplejwt.authentication.JWTAuthentication',  # para móvil/API
    'rest_framework.authentication.SessionAuthentication',         # para browser
  ),
}
```

- **Browser**: session cookie (Django login) → `credentials: 'same-origin'` en fetch
- **Móvil/API**: POST a `/api/v1/auth/login/` → JWT en Bearer header

## Decisiones arquitectónicas

| Decisión | Justificación |
|----------|---------------|
| Monolito modular (no microservicios) | 440 usuarios, un solo dominio. Overkill distribuir |
| PostgreSQL en prod, SQLite en dev | pgvector para recomendaciones IA (Fase 11) |
| DRF (no FastAPI/GraphQL) | Integración nativa Django + ORM + admin |
| SessionAuth + JWT dual | Compatibilidad browser y móvil sin duplicar |
| Strategy para PDF | Open/Closed para agregar plantillas sin tocar código existente |
| Auditoría automática en ViewSets | Trazabilidad sin ensuciar cada endpoint |

## Testing

```bash
pytest                          # corre todos los tests
pytest tests/test_pdf_strategy.py   # solo PDFs
pytest -k audit                     # solo los que matcheen "audit"
```

Cobertura actual: **managers, auth, sessions CRUD, PDF Strategy, auditoría**.
Tests usan `factory-boy` para fixtures (ver `tests/factories.py`) y `pytest-django`
para DB transaccional.

## CI/CD

`.github/workflows/ci.yml` corre en cada push/PR a `main` o `tesis`:

- Matrix Python 3.10, 3.11, 3.12
- `manage.py check` — sin warnings críticos
- `makemigrations --check --dry-run` — migraciones al día
- `pytest --tb=short`
- `ruff check` — linting

## Deploy

Railway con `railway.json`:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:$PORT
```

Env vars requeridas:
- `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`
- `DATABASE_URL` (Railway inyecta)
- `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `SITE_URL`
- Opcional: `SENTRY_DSN`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

## Auditoría automática

Cada escritura en recursos admin genera una entry en `Auditoria`:

```
usuario   acción           detalle                          fecha
admin     CREAR_SESION     Sesión #5 (Test - 2026-04-20)   2026-04-18 15:23
admin     TOGGLE_SESION    Sesión #5 → activa=False         2026-04-18 15:25
admin     BULK_PDF_SESION  Sesión #5: 42 PDFs merged       2026-04-18 15:30
```

Accesible via `GET /api/v1/admin/audit/` con filtros por acción, usuario, fecha.

## Roadmap de IA (Fases 8-12, scaffold en `core/services/ai/`)

1. **Copilot** — cuerpo certificado (Claude Haiku)
2. **Excel mapper** — clasifica columnas por contenido
3. **Dashboard insights** — narrativa ejecutiva de métricas
4. **Recomendaciones** — content-based con embeddings OpenAI + pgvector
5. **Voice commands** — crear sesión por voz (Web Speech API + Claude tool use)

Endpoints placeholder ya expuestos en `/api/v1/admin/ai/*` con HTTP 501 hasta
configurar `ANTHROPIC_API_KEY`.
