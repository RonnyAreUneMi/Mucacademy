# Deploy en Railway — CertifAI

Backend en Railway con **4 servicios**: `web` (Django) + `worker` (Celery) +
**Postgres** + **Redis**. La app móvil se conecta a la URL pública HTTPS que
da Railway (no hace falta dominio propio).

> El `beat` (tareas programadas tipo cron) **no se sube** — no es necesario para
> el demo/documentación y ahorra un servicio.

---

## 0. Requisito previo — subir el repo a GitHub

Railway despliega desde GitHub. Primero commiteá y pusheá la estructura actual
(`server/` + `mobile/`). La rama a conectar en Railway será `tesis` (o `main`).

---

## 1. Crear el proyecto

1. Entrá a https://railway.app → **New Project** → **Deploy from GitHub repo**.
2. Elegí el repo `CertifAi22` y la rama `tesis`.
3. Railway crea el primer servicio (será el **web**).

## 2. Configurar el servicio `web`

En el servicio → **Settings**:
- **Root Directory** = `server`  ← imprescindible (el backend vive ahí).
- El **Start Command** ya viene de `server/railway.json` (migrate + collectstatic
  + superusuario + gunicorn). No lo toques.

## 3. Agregar Postgres y Redis (plugins gestionados)

En el proyecto → **New** → **Database**:
- **Add PostgreSQL** → expone `DATABASE_URL`.
- **Add Redis** → expone `REDIS_URL`.

## 4. Variables de entorno del `web`

En el servicio web → **Variables**:

| Variable | Valor |
|---|---|
| `SECRET_KEY` | (una clave larga aleatoria) |
| `DEBUG` | `False` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `CELERY_BROKER_URL` | `${{Redis.REDIS_URL}}` |
| `CELERY_RESULT_BACKEND` | `${{Redis.REDIS_URL}}` |
| `CELERY_TASK_ALWAYS_EAGER` | `False`  ← clave: así el worker procesa |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_OAUTH_EMAIL` | (si usás login/emails Google) |
| `GOOGLE_REDIRECT_URI` | `https://<tu-url>.up.railway.app/panel/google/callback/` |
| `EMAIL_*` | (si usás envío de correos) |

> **No hace falta setear `ALLOWED_HOSTS`**: `settings.py` agrega solo el dominio
> de Railway (`RAILWAY_PUBLIC_DOMAIN`) y arma `CSRF_TRUSTED_ORIGINS` con HTTPS.

## 5. Agregar el servicio `worker` (Celery)

En el proyecto → **New** → **GitHub Repo** (el mismo repo/rama) → segundo servicio:
- **Root Directory** = `server`.
- **Start Command** (override en Settings): 
  ```
  celery -A config worker -l info --concurrency=1
  ```
- **Variables**: las mismas que el web →
  `SECRET_KEY`, `DATABASE_URL=${{Postgres.DATABASE_URL}}`,
  `CELERY_BROKER_URL=${{Redis.REDIS_URL}}`,
  `CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}`, `DEBUG=False`,
  `CELERY_TASK_ALWAYS_EAGER=False`.
  (El worker no necesita `PORT` ni gunicorn.)

## 6. Deploy y URL pública

1. Railway construye y despliega. En el servicio web → **Settings → Networking**
   → **Generate Domain** → te da `https://<algo>.up.railway.app`.
2. Verificá: abrí esa URL (debe cargar la landing) y `…/panel/` (admin).
   - Usuario admin por defecto: lo crea `create_default_superuser` (revisá ese
     comando para las credenciales, o creá uno con `railway run python manage.py createsuperuser`).

## 7. Conectar la app móvil

En [`mobile/app.json`](mobile/app.json) → `extra.apiBaseUrl`:
```json
"apiBaseUrl": "https://<tu-url>.up.railway.app"
```
Luego, para presentar en Android sin Expo Go, generá un APK:
```bash
cd mobile
eas build -p android --profile preview
```
O corré `npx expo start` en tu laptop durante la defensa (gratis). Como el
backend es público, funciona desde cualquier red.

---

## Costos / ahorro

- 4 servicios 24/7 ≈ **~$13-16/mes**; para tu ventana de ~2-3 semanas ≈ **~$9-13**.
- Cuando termine la documentación/capturas, **pausá los servicios** (Railway
  cobra por tiempo de uso) y volvé a prenderlos la semana de la sustentación.
- `--concurrency=1` en el worker reduce RAM (menos costo).
