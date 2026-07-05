# ADR-001 · Monolito modular vs microservicios

- **Estado**: Aceptado
- **Fecha**: 2026-04-15
- **Decisores**: Equipo CertifAI

## Contexto

El sistema gestiona varios sub-dominios claramente separables:
participantes · sesiones académicas · certificados · firmas digitales ·
integraciones (Google Workspace, IA). En frameworks modernos (Kubernetes,
service mesh) la elección por defecto suele ser microservicios.

Sin embargo, los datos de estos dominios están **fuertemente relacionados**:
un certificado pertenece a un lote, que pertenece a una sesión, que tiene
participantes confirmados. Romper esa coherencia transaccional aumenta la
complejidad operativa sin beneficio claro a la escala del proyecto.

## Decisión

Implementamos un **monolito modular en capas** con bounded contexts
materializados como **apps de Django** (`core`, `api`, `admin_panel`,
`public`). La capa de servicios (`core/services/*`) aísla las integraciones
externas detrás de interfaces estables.

## Consecuencias

### Positivas

- **Consistencia transaccional**: una sola DB con FKs garantiza coherencia
  fuerte (atomicidad en `generate_batch` con bulk_create + asociación a sesión).
- **Latencia interna mínima**: function calls in-process en vez de RPC sobre red.
- **Operación simple**: un solo deploy (gunicorn + worker + beat), un solo log,
  un solo monitoring.
- **Modular dentro del monolito**: cada bounded context vive en su carpeta,
  las dependencias cruzadas son explícitas (imports), no hay acoplamiento
  oculto vía DB compartida tipo "todos pueden tocar todo".

### Negativas

- **Escalado uniforme**: si la generación de PDFs satura CPU, escalamos toda
  la app, no sólo ese servicio.
- **Despliegue acoplado**: un bug en un módulo afecta todo el sistema hasta
  hacer rollback.
- **Tope de tamaño**: cuando el equipo crezca a >10 devs, los conflictos en
  el repo monolítico aumentarán.

### Mitigaciones

- Servicios computacionalmente costosos (PDFs, IA, envío masivo de correos)
  ya están **encapsulados detrás de interfaces** — son candidatos naturales
  para extracción a microservicios cuando justifique.
- Las **tareas Celery** ya distribuyen el load de I/O (Gmail API, IA) sin
  tocar el monolito principal.
- El **API REST público y privado** son la única forma de acceso al dominio
  desde fuera, así que un futuro split puede mantener compatibilidad.

## Alternativas consideradas

- **Microservicios desde día 0** — descartado por complejidad operativa
  desproporcionada para el alcance del proyecto.
- **Monolito spaghetti (sin apps separadas)** — descartado por imposibilidad
  de testear contextos en aislamiento.

## Referencias

- Sam Newman · *Monolith to Microservices* (2019), cap. "Modular Monolith First"
