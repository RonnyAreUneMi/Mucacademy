# ADR-002 · Django REST Framework vs FastAPI

- **Estado**: Aceptado
- **Fecha**: 2026-04-15

## Contexto

FastAPI es la opción "trendy" para APIs Python (async, type hints, OpenAPI
automática). Pero el proyecto ya está construido sobre Django (admin,
templates, ORM, middleware, sesiones, autenticación, sistema de migraciones).

## Decisión

**Django REST Framework** sobre el mismo proyecto Django, no un servicio
separado en FastAPI.

## Consecuencias

### Positivas

- **Reuso completo del modelo**: los serializers de DRF consumen los mismos
  ORM models que las vistas Django Templates. Sin duplicación.
- **Auth unificada**: `SessionAuthentication` de DRF reusa la sesión Django
  del admin panel; los participantes públicos usan su propia sesión via
  middleware. JWT vía `simplejwt` se monta encima sin fricción.
- **Migraciones, signals, admin**: todo ya viene resuelto.
- **drf-spectacular** genera OpenAPI 3 + Swagger UI a partir de las views,
  similar a FastAPI pero sin reescribir nada.
- **Ecosistema maduro**: pagination, filters, throttling, permissions
  están bien probados.

### Negativas

- **Async limitado**: Django sólo recientemente soporta vistas async; DRF
  tiene soporte experimental. FastAPI sería más rápido en endpoints
  I/O-bound. **Mitigación**: las operaciones lentas (envío de correos,
  IA, generación de PDFs) van por **Celery**, no por endpoints async.
- **Boilerplate**: ViewSets + Routers + Serializers son más verbosos que
  los path operations de FastAPI con Pydantic.

## Alternativas consideradas

- **FastAPI separado + Django admin** — descartado: duplicaría auth,
  modelos vía SQLAlchemy o reuso de Django ORM con hacks, y sería un
  segundo deploy.
- **Django Ninja** — más liviano que DRF y similar a FastAPI, pero menos
  maduro y la integración con `simplejwt` requiere parches.
