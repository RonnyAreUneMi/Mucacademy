# ADR-005 · Tailwind CDN vs bundler

- **Estado**: Aceptado (con plan de migración futura)
- **Fecha**: 2026-04-29

## Contexto

El frontend del proyecto se construye con **Tailwind CSS** + JavaScript
vanilla. Tailwind se puede usar de tres maneras:

1. **CDN runtime** — `<script src="cdn.tailwindcss.com">` compila JIT en
   el browser.
2. **Bundler con CLI** — `tailwindcss -i input.css -o output.css` produce
   un CSS con sólo las clases usadas.
3. **PostCSS pipeline** + Vite/Webpack — full SPA-style.

## Decisión

**Tailwind CDN runtime durante el desarrollo y MVP** de la tesis. Plan
documentado para migrar a CLI bundleado antes de producción seria.

## Consecuencias

### Positivas (CDN)

- **Cero build step**: editar template → recargar página → ver cambios.
- **Sin Node.js, sin npm, sin webpack** en el proyecto.
- **Iteración velocísima**: probar arbitrary values (`top-[13px]`,
  `bg-[#162054]`) sin recompilar.
- **Demo y deployment simplísimos**: sólo hay que servir Django, no hay
  pipeline JS.

### Negativas (CDN)

- **Performance**: Tailwind JIT runtime pesa ~250KB y se ejecuta en cada
  page load. En conexiones lentas se nota.
- **FOUC (Flash of Unstyled Content)**: durante 100-300ms la página se
  ve sin estilos hasta que JIT termine.
- **Dependencia externa**: si el CDN cae o tiene latencia, la UI se rompe
  para todos los usuarios.
- **Sin tree-shaking real**: clases que ya no se usan no se purgan
  (irrelevante en modo CDN, donde nada se purga).
- **Inline styles dispersos**: en vez de una hoja CSS, cada template
  acumula classes Tailwind largas. Lectura más densa.

### Mitigaciones (futuras, fuera del alcance de la tesis)

Cuando el proyecto vaya a producción real:

1. **Setup `tailwind.config.js` + CLI**:
   ```bash
   npm i -D tailwindcss
   npx tailwindcss init
   npx tailwindcss -i input.css -o static/css/app.css --minify
   ```
2. **Reemplazar `<script src="cdn.tailwind...">` por `<link rel="stylesheet">`**.
3. **Build automatizado en Docker** (multi-stage build con Node).
4. **CI** que falle si hay clases con utilities arbitrarias raras (
   detector de class-strings auto-generadas).

## Por qué se aceptó esta deuda técnica

- El proyecto es una **tesis de grado**, no producción comercial inmediata.
- El usuario crítico es el **tribunal**, que ve la app local sin importar
  los 200ms de FOUC.
- Migrar a bundler antes de tener el dominio cerrado obligaría a re-ajustar
  configs en cada iteración de UI.
- Los 200ms de FOUC y el peso del JIT no afectan la calidad arquitectónica
  ni la corrección funcional.

## Referencias

- [Tailwind CSS · Installation: Play CDN](https://tailwindcss.com/docs/installation/play-cdn)
- [Web Vitals · CLS y FOUC](https://web.dev/articles/cls)
