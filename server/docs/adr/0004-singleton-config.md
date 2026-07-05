# ADR-004 · Singleton Config (Design System · IA · Google · Diseño)

- **Estado**: Aceptado
- **Fecha**: 2026-04-25

## Contexto

Hay configuración que es **única en el sistema** y debe ser editable por
el admin sin tocar `.env`/`settings.py`/redeploy:

- **Tokens del Design System** (colores, fuentes, radios) que alimentan
  el `:root` CSS de toda la UI.
- **Credenciales Google OAuth de la cuenta institucional** (la que crea
  los Meets y manda los correos).
- **Proveedor de IA activo** (Claude / OpenAI / Groq) + API key.
- **Diseño global del certificado** (plantilla, colores, firmas
  institucionales por defecto).

Todas son configuraciones globales: existe **una sola fila**, no se borran,
se editan.

## Decisión

Definimos un mixin abstracto `SingletonModel` en `core/base/models.py`:

```python
class SingletonModel(models.Model):
    class Meta:
        abstract = True

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
```

Modelos que lo implementan:

- `UIDesignTokens` (colores · fuentes · radios)
- `GoogleCredential` (access + refresh tokens)
- `AIConfig` (proveedor activo · API key · modelo)
- `DisenoGlobal` (template default de certificado)

## Consecuencias

### Positivas

- **`get_or_create(pk=1)` siempre devuelve el mismo objeto** — los views
  pueden llamar `UIDesignTokens.get_solo()` sin chequear existencia.
- **Editable desde el admin Django** o desde la pantalla custom
  (`/panel/design-system/`, `/panel/ai/config/`) sin migrations.
- **Inyección automática a templates** vía context processors:
  `{{ design.color_brand }}` está disponible en todas las plantillas
  del panel.
- **Save() forzando pk=1** garantiza que aunque alguien intente crear
  un duplicado por error, sigue siendo singleton.

### Negativas

- **No es thread-safe en escritura concurrente**: dos requests editando
  al mismo tiempo pueden tener race condition. **Mitigación**: estos
  configs cambian rara vez, no es un cuello.
- **No multi-tenant**: si en el futuro CertifAI sirve múltiples
  universidades, `Singleton` deja de tener sentido — habría que migrar
  a un modelo con `tenant_id` y eliminar `pk=1` forzado.

### Mitigaciones

- Actualmente la app es single-tenant (UNEMI). Si se vuelve multi-tenant,
  el cambio se concentra en `SingletonModel` y los modelos que lo usan —
  no se filtra por todo el código.
