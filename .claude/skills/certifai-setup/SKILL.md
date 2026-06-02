---
name: certifai-setup
description: Set up and run the CertifAI project (Django backend + Expo mobile app) on a fresh machine. Use when cloning the repo on a new computer, configuring the env, migrating the DB, creating an admin, or starting the web/mobile servers. Covers the refactor/english-rewrite branch.
---

# CertifAI · Setup & Run

How to get CertifAI running from scratch on any machine. Full version lives in
`docs/SETUP_OTRA_MAQUINA.md`; this skill is the fast path.

Project = **Django backend** (web + REST API) + **Expo/React Native mobile app**.
Working branch: **`refactor/english-rewrite`** (all code identifiers in English).

## When to use
- Cloning the repo on a new computer
- Setting up `.env`, venv, DB migrations, admin user
- Starting the Django server and/or the Expo mobile app
- Diagnosing "app stuck loading", `DisallowedHost`, or Google OAuth errors

## Prerequisites
Python 3.10+, Node 18+, Git. Optional: Redis 7+ (only for async AI summaries),
Expo Go on the phone.

## Backend — step by step

```bash
# 1. Clone + branch
git clone https://github.com/RonnyAreMC/CertifAi22.git
cd CertifAi22
git checkout refactor/english-rewrite

# 2. venv + deps
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Create `.env` in the project root (NOT in git — has secrets):

```env
DEBUG=True
SECRET_KEY=dev-local-key-change-me
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
SECURE_SSL_REDIRECT=False
GOOGLE_CLIENT_ID=<from console.cloud.google.com/apis/credentials>
GOOGLE_CLIENT_SECRET=<GOCSPX-...>
GOOGLE_REDIRECT_URI=http://localhost:8500/panel/google/callback/
GOOGLE_OAUTH_EMAIL=<account@unemi.edu.ec>
GOOGLE_PROJECT_ID=pasantia-483716
```

```bash
# 3. DB (creates tables + seeds 5 faculties)
python manage.py migrate

# 4. Admin user
python manage.py shell -c "from core.models import User; u=User.objects.create_superuser('admin','admin@admin.com','admin12345'); u.role='superadmin'; u.save()"

# 5. Run
python manage.py runserver 0.0.0.0:8500
```

URLs: landing `/` · participant login `/cuenta/login/` · admin panel `/panel/`
· Django admin `/admin/`. Always open via **localhost** (not 127.0.0.1) to match
OAuth config.

## Mobile — step by step

```bash
cd mobile
npm install --legacy-peer-deps
```

Edit `mobile/app.json` → `extra.apiBaseUrl` to your machine's **LAN IP** (run
`ipconfig` / `ifconfig`), e.g. `http://192.168.1.50:8500`. Add that same IP to
`ALLOWED_HOSTS` in `.env` and restart Django.

```bash
npx expo start          # scan QR with Expo Go (same WiFi)
# npx expo start --tunnel   # if WiFi won't connect
```

## Verify

```bash
python manage.py check          # no issues
python -m pytest -q             # 45 passed
cd mobile && npx tsc --noEmit   # exit 0
```

## Key facts
- **Models are English**: `User`, `Participant`, `Certificate`, `CertificateBatch`,
  `Event`, `Speaker`, `Attendance`, `Enrollment`, `SessionSummary`, `QuizAttempt`,
  `Signature`, `GlobalDesign`, `AuditLog`, `Faculty`. `AUTH_USER_MODEL = core.User`.
- **DB is reset-friendly**: dropping `db.sqlite3` + `migrate` rebuilds clean.
- **AI summaries** need Redis + Celery worker + an AI provider configured at
  `/panel/ai/config/`:
  ```bash
  python -m celery -A config worker -l info --pool=solo
  python -m celery -A config beat -l info --schedule=/tmp/celerybeat-schedule
  ```
- **Design mockups**: open `figma-exports/04-mobile/00-index.html` to browse all
  12 mobile screens (gallery with sidebar + preview).

## Common errors
| Symptom | Fix |
|---|---|
| `DisallowedHost` / HTTP 400 | add the host to `ALLOWED_HOSTS` in `.env`, restart |
| Mobile app stuck loading | wrong `apiBaseUrl` in `app.json` (use current LAN IP, not localhost) |
| Google `redirect_uri_mismatch` | register the exact callback URL+port in Google Console |
| Google `invalid_client` | secret was invalidated — generate a new one in the console |
| `npm install` fails | use `--legacy-peer-deps` |
| Port 8500 busy | use another port (e.g. 8501) and update `GOOGLE_REDIRECT_URI` + Console |
