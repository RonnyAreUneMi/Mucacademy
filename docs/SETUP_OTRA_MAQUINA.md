# Guía · Levantar CertifAI en otra máquina (rama `refactor/english-rewrite`)

Pasos para clonar y correr el proyecto completo (backend Django + app móvil Expo)
desde cero en una computadora nueva.

> Rama de trabajo actual: **`refactor/english-rewrite`** (todo en inglés).
> Cuando la mergees a `tesis`, reemplazá el nombre donde diga la rama.

---

## 0. Requisitos previos

Instalá en la máquina nueva:

| Herramienta | Versión | Para qué |
|---|---|---|
| **Python** | 3.10+ | Backend Django |
| **Node.js** | 18+ (LTS) | App móvil Expo |
| **Git** | cualquiera | Clonar el repo |
| **Redis** (opcional) | 7+ | Tareas async (resúmenes IA). Sin esto, las tareas corren en modo síncrono en DEBUG |
| **Expo Go** (en el celular) | última | Probar la app móvil |

---

## 1. Clonar el repo y pararse en la rama

```bash
git clone https://github.com/RonnyAreMC/CertifAi22.git
cd CertifAi22
git checkout refactor/english-rewrite
```

---

## 2. Backend (Django)

### 2.1 Crear el entorno virtual e instalar dependencias

```powershell
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
# Mac / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2 Crear el archivo `.env`

El `.env` NO está en git (tiene secretos). Crealo en la raíz del proyecto:

```env
DEBUG=True
SECRET_KEY=dev-local-key-cambiar-en-produccion
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
SECURE_SSL_REDIRECT=False

# ── Google OAuth (Calendar + Drive + Docs) ──
# Sacá estos valores de https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-tu-secret
GOOGLE_REDIRECT_URI=http://localhost:8500/panel/google/callback/
GOOGLE_OAUTH_EMAIL=tu-cuenta@unemi.edu.ec
GOOGLE_PROJECT_ID=pasantia-483716
```

> **Importante**: el `GOOGLE_CLIENT_SECRET` se invalida si queda expuesto
> públicamente. Si Google lo rechazó (`invalid_client`), generá uno nuevo
> en la consola y pegalo acá.

### 2.3 Migrar la base de datos y crear datos

```bash
python manage.py migrate
```

Esto crea la BD (SQLite por defecto) con todas las tablas en inglés y siembra
las 5 facultades automáticamente.

**Crear un superusuario admin:**
```bash
python manage.py createsuperuser
# username: admin
# email: admin@admin.com
# password: (el que quieras)
```

O por shell rápido:
```bash
python manage.py shell -c "from core.models import User; u=User.objects.create_superuser('admin','admin@admin.com','admin12345'); u.role='superadmin'; u.save()"
```

### 2.4 Levantar el servidor

```bash
python manage.py runserver 0.0.0.0:8500
```

URLs:
- Web pública / landing: http://localhost:8500/
- Login participante: http://localhost:8500/cuenta/login/
- Panel admin: http://localhost:8500/panel/
- Django admin: http://localhost:8500/admin/

> Si el puerto 8500 está ocupado, usá otro (ej. `8501`) y actualizá
> `GOOGLE_REDIRECT_URI` + los redirect URIs en Google Console a ese puerto.

### 2.5 (Opcional) Celery para resúmenes IA automáticos

Solo si vas a usar el pipeline Drive → transcript → IA. Necesita Redis corriendo.

```bash
# Terminal 2 — worker
.venv\Scripts\python.exe -m celery -A config worker -l info --pool=solo

# Terminal 3 — scheduler (procesa eventos terminados cada 30 min)
.venv\Scripts\python.exe -m celery -A config beat -l info --schedule=/tmp/celerybeat-schedule
```

También configurá la IA en `/panel/ai/config/` (proveedor + API key de OpenAI o Claude).

---

## 3. App móvil (Expo)

### 3.1 Instalar dependencias

```bash
cd mobile
npm install --legacy-peer-deps
```

### 3.2 Apuntar la app al backend

Editá `mobile/app.json` → `extra.apiBaseUrl` con la **IP local de tu máquina**
(no `localhost`, el celular no lo entiende):

```json
"extra": {
  "apiBaseUrl": "http://192.168.X.X:8500"
}
```

Para saber tu IP:
```bash
# Windows
ipconfig        # buscá "Dirección IPv4" de tu WiFi
# Mac/Linux
ifconfig | grep "inet "
```

Y agregá esa IP a `ALLOWED_HOSTS` en el `.env`:
```env
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,192.168.X.X
```
(reiniciá el server Django tras editar `.env`).

### 3.3 Arrancar Expo

```bash
npx expo start
```

- Escaneá el QR con **Expo Go** (Android) o la **cámara** (iOS).
- El celular y la PC deben estar en la **misma red WiFi**.
- Si no conecta: `npx expo start --tunnel` (más lento pero atraviesa cualquier red).

---

## 4. Verificar que todo anda

```bash
# Backend
python manage.py check          # debe decir "no issues"
python -m pytest -q             # 45 passed

# Mobile
cd mobile && npx tsc --noEmit   # exit 0 (sin errores)
```

---

## 5. Credenciales de prueba (si usás el seed)

| Tipo | Usuario | Contraseña |
|---|---|---|
| Admin | `admin` | la que pusiste en createsuperuser |
| Participante demo | `test@unemi.edu.ec` | `demo12345` |

Para sembrar el participante demo + eventos:
```bash
python manage.py shell < scripts/seed_demo_account.py
```

---

## 6. Mockups de diseño (Figma)

Los mockups estáticos de las pantallas móviles están en
`figma-exports/04-mobile/`. Abrí **`00-index.html`** en el navegador para
ver la galería con todas las pantallas (menú a la izquierda + preview).
Para importar a Figma: plugin **html.to.design**.

---

## 7. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `DisallowedHost` / 400 | falta tu host en `ALLOWED_HOSTS` | agregalo al `.env` y reiniciá |
| App móvil "cargando" infinito | `apiBaseUrl` con IP vieja o `localhost` | poné tu IP actual en `app.json` |
| Google `redirect_uri_mismatch` | el puerto/host no está en Google Console | registrá la URL exacta del callback |
| Google `invalid_client` | el client secret fue invalidado | generá uno nuevo en la consola |
| `npm install` falla | conflicto de peer deps | usá `--legacy-peer-deps` |
| Tareas IA no corren | falta Redis o Celery worker | arrancá Redis + el worker |

---

## 8. Estructura del proyecto (referencia)

```
CertifAi22/
├── config/              # settings, urls, celery
├── core/                # modelos, managers, services, tasks (todo en inglés)
│   ├── models/          # User, Participant, Certificate, Event, etc.
│   ├── managers/
│   ├── services/        # pdf, ai, meet, email
│   └── tasks/           # Celery
├── api/                 # DRF (admin + public endpoints)
├── public/              # vistas web del participante (/cuenta/)
├── admin_panel/         # panel admin custom (/panel/)
├── templates/           # emails
├── mobile/              # app Expo/React Native (TypeScript)
├── figma-exports/04-mobile/  # mockups de diseño
└── docs/                # esta guía + arquitectura + modelo BD
```
