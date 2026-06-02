# Refactor Mapping — Spanish → English (CertifAI)

Authoritative reference for translating ALL code identifiers from Spanish to
English. The new model files (`core/models/`, `core/managers/`, `core/admin.py`,
`core/validators.py`, `core/base/`) are ALREADY rewritten — do NOT touch those.

## Rules
1. Rename only **code identifiers** (model classes, field names, related_name,
   manager methods, enum members, query kwargs, attribute access, serializer
   field lists, dict keys that map to model fields, template variables that
   access model attributes).
2. **Keep user-facing Spanish display strings** (labels, messages shown to end
   users, certificate body text, faculty proper names like "FACI - Ingeniería").
   Those are data, not code.
3. Keep behavior identical. Do not refactor logic.
4. Comments/docstrings: translate if trivial; otherwise leave. Not critical.
5. Import paths: `from core.models import X` — update X to the new name.

## Model classes

| Spanish | English |
|---|---|
| `Usuario` | `User` |
| `SolicitudAcceso` | `AccessRequest` |
| `Participante` | `Participant` |
| `ParticipanteToken` | `ParticipantToken` |
| `LoteCertificados` | `CertificateBatch` |
| `Certificado` | `Certificate` |
| `FirmaInstitucional` | `Signature` |
| `DisenoGlobal` | `GlobalDesign` |
| `SesionAsistencia` | `Event` |
| `Ponente` | `Speaker` |
| `RegistroAsistencia` | `Attendance` |
| `ConfirmacionAsistencia` | `Enrollment` |
| `ResumenSesion` | `SessionSummary` |
| `EstadoProcesamiento` | `ProcessingStatus` |
| `IntentoCuestionario` | `QuizAttempt` |
| `Auditoria` | `AuditLog` |
| `GoogleCredential` | `GoogleCredential` (unchanged) |
| `AIConfig`, `AIProvider`, `PROVIDER_MODELS`, `UIDesignTokens` | unchanged |
| `FACULTADES_CHOICES` | `FACULTY_CHOICES` |
| `Facultad` | `Faculty` |

## Enums

| Spanish | English |
|---|---|
| `Rol` | `AdminRole` (members SUPERADMIN/ADMIN same; values 'superadmin'/'admin' same) |
| `EstadoSolicitud` | `AccessRequestStatus`: PENDIENTE→PENDING('pending'), APROBADO→APPROVED('approved'), RECHAZADO→REJECTED('rejected') |
| `Plantilla` | `CertificateTemplate`: CLASICO→CLASSIC('classic'), MODERNO→MODERN('modern'), GEOMETRICO→GEOMETRIC('geometric') |
| `Modalidad` | `EventModality`: PRESENCIAL→IN_PERSON('in_person'), VIRTUAL→VIRTUAL('virtual') |
| `PlataformaVirtual` | `VirtualPlatform`: ZOOM/MEET/TEAMS same, OTRO→OTHER('other') |
| `EstadoProcesamiento` | `ProcessingStatus`: PENDIENTE→PENDING('pending'), BUSCANDO→SEARCHING('searching'), PROCESANDO→PROCESSING('processing'), LISTO→READY('ready'), SIN_TRANSCRIPT→NO_TRANSCRIPT('no_transcript'), FALLIDO→FAILED('failed') |
| `DiaSemana` | REMOVED — `Event.day_of_week` is now a derived property (no field) |
| `Auditoria.accion` values | `AuditAction`: CREAR→CREATE, EDITAR→UPDATE, ELIMINAR→DELETE, APROBAR→APPROVE, RECHAZAR→REJECT (also CREAR_SESION etc → use CREATE) |

Enums import path: `from core.models.catalogs.enums import ...` or `from core.models import ...` (re-exported: FACULTY_CHOICES, Faculty). Other enums import from `core.models.catalogs.enums`. ProcessingStatus & AuditAction import from `core.models`.

## Field renames by model

### User (was Usuario) — AbstractUser
`rol`→`role`, `facultad`→`faculty`, `telefono`→`phone`.
DROPPED fields (use AbstractUser built-ins): `fecha_creacion`→`date_joined`, `ultimo_acceso`→`last_login`, `activo`→`is_active`.
Property `es_superadmin`→`is_superadmin`, `nombre_completo`→`full_name`.

### AccessRequest (was SolicitudAcceso)
`nombres`→`first_name`, `apellidos`→`last_name`, `telefono`→`phone`, `facultad`→`faculty`, `estado`→`status`, `usuario_creado`→`created_user`, `fecha_solicitud`→`requested_at`, `fecha_respuesta`→`responded_at`, `aprobado_por`→`approved_by`, `motivo_rechazo`→`rejection_reason`. Property `nombre_completo`→`full_name`. related_name `solicitud_acceso`→`access_request`, `solicitudes_aprobadas`→`approved_requests`.

### Participant (was Participante)
`cedula`→`national_id`, `nombres`→`first_name`, `apellidos`→`last_name`, `celular`→`phone`, `es_lider`→`is_leader`. Props `nombre_completo`→`full_name`, `has_account` same, `initials` same. related_name `tokens` same.

### ParticipantToken
`participante`→`participant`. `generate_for` same. `is_expired` same.

### CertificateBatch (was LoteCertificados)
`nombre_lote`→`name`, `fecha_creacion`→`created_at`, `archivo_excel`→`excel_file`, `administrador`→`administrator`, `activo`→`is_active`, `facultad`→`faculty`, `personalizar_diseno`→`customize_design`, `plantilla`→`template`, `color_primario`→`color_primary`, `color_secundario`→`color_secondary`, `color_terciario`→`color_tertiary`, `color_texto`→`color_text`, `cuerpo_certificado`→`body_text`, `firma_inst_N`→`signature_inst_N`, `nombre_firma_N`→`signature_name_N`, `cargo_firma_N`→`signature_role_N`, `imagen_firma_N`→`signature_image_N`, `logo_header_N`→`header_logo_N`, `posicion_firmas`→`signatures_position`. Property `firmas_activas`→`active_signatures` (its dict keys: `slot` same, `nombre`→`name`, `cargo`→`role`, `imagen`→`image`). related_name `certificados`→`certificates`, `sesiones`→`events`, `lotes_firma1..4`→`batches_slot1..4`.

### Certificate (was Certificado)
`lote`→`batch`, `participante`→`participant`, `cedula`→`national_id`, `nombres`→`first_name`, `apellidos`→`last_name`, `celular`→`phone`, `curso`→`course`, `fecha_curso`→`course_date`, `horas`→`hours`, `hash_verificacion`→`verification_hash`, `pdf_generado`→`pdf_file`, `descargas_count`→`download_count`, `veces_buscado`→`search_count`, `fecha_ultima_descarga`→`last_download_at`. Props `nombre_completo`→`full_name`, `fue_descargado`→`was_downloaded`. related_name `asistencias`→`attendances`, `confirmaciones`→`enrollments`.

### Signature (was FirmaInstitucional)
`nombre`→`name`, `cargo`→`role`, `imagen`→`image`, `activa`→`is_active`, `orden`→`sort_order`, `fecha_creacion`→`created_at`.

### GlobalDesign (was DisenoGlobal)
`color_*` same as batch; `plantilla`→`template`, `cuerpo_certificado`→`body_text`, `firma_inst_N`→`signature_inst_N`, `nombre_firma_4`→`signature_name_4`, `cargo_firma_4`→`signature_role_4`, `imagen_firma_4`→`signature_image_4`, `logo_header_N`→`header_logo_N`, `posicion_firmas`→`signatures_position`, `firma_N_offset_y`→`signature_N_offset_y`, `firma_N_escala`→`signature_N_scale`. related_name `diseno_firma1..3`→`design_slot1..3`. Classmethod `get_solo()` is now `load()` (SingletonModel).

### Event (was SesionAsistencia)
`lote`→`batch`, `titulo`→`title`, `descripcion`→`description`, `imagen_banner`→`banner_image`, `modalidad`→`modality`, `plataforma_virtual`→`virtual_platform`, `enlace_virtual`→`meeting_url`, `lugar`→`location`, `fecha`→`date`, `hora_inicio`→`start_time`, `hora_fin`→`end_time`, `codigo_qr`→`qr_code`, `capacidad`→`capacity`, `solo_lideres`→`leaders_only`, `activa`→`is_active`, `transcripcion_habilitada`→`transcription_enabled`, `google_calendar_event_id` same. Props: `dia_semana`→`day_of_week`, `label` same, `capacidad_ilimitada`→`is_unlimited`, `confirmados_count`→`enrolled_count`, `cupos_disponibles`→`available_seats`, `esta_llena`→`is_full`, `es_virtual`→`is_virtual`, `plataforma_display_safe`→`platform_display_safe`. related_name `ponentes`→`speakers`, `registros`→`attendances`, `confirmaciones`→`enrollments`, `resumen`→`summary`.

### Speaker (was Ponente)
`sesion`→`event`, `nombre`→`name`, `titulo`→`title`, `afiliacion`→`affiliation`, `bio` same, `orden`→`sort_order`. Prop `display_name` same.

### Attendance (was RegistroAsistencia)
`sesion`→`event`, `certificado`→`certificate`, `participante`→`participant`, `fecha_registro`→`registered_at`, `ip_address` same.

### Enrollment (was ConfirmacionAsistencia)
`certificado`→`certificate`, `participante`→`participant`, `sesion`→`event`, `confirmado`→`confirmed`, `bloqueado`→`blocked`, `fecha_confirmacion`→`enrolled_at`.

### SessionSummary (was ResumenSesion)
`sesion`→`event`, `drive_file_id`/`drive_file_name`/`transcript_raw`/`transcript_chars` same, `resumen_md`→`summary_md`, `puntos_clave`→`key_points`, `proximos_pasos`→`next_steps`, `cuestionario`→`quiz`, `duracion_minutos`→`duration_minutes`, `estado`→`status`, `error_msg` same, `procesado_at`→`processed_at`, `ai_model`/`ai_input_tokens`/`ai_output_tokens` same. Props `is_ready`/`has_failed` same.

### QuizAttempt (was IntentoCuestionario)
`participante`→`participant`, `sesion`→`event`, `correctas`→`correct`, `total` same, `tiempo_total_seg`→`total_time_seconds`, `respuestas`→`answers`. Prop `porcentaje`→`percentage`. Const `MAX_INTENTOS`→`MAX_ATTEMPTS`. related_name `intentos_cuestionario`→`quiz_attempts`.

### AuditLog (was Auditoria)
`usuario`→`user`, `accion`→`action`, `detalle`→`details`, `fecha`→`created_at`. New fields: `content_type`, `object_id`, `target`, `changes`, `ip`, `user_agent`. related_name `acciones_auditoria`→`audit_logs`.

## Managers
`CertificadoManager`→`CertificateManager`, `ParticipanteManager`→`ParticipantManager`, `LoteManager`→`BatchManager`, `SesionManager`→`EventManager`. Method `lideres()`→`leaders()`. Annotation aliases: `total_certificados`→`certificates_total`, `total_confirmados`→`enrolled_total`, `total_asistentes`→`attendees_total`, `certificados_total`→`certificates_total`.

## Celery tasks (core/tasks/transcript_tasks.py — file keeps name)
`procesar_transcript_sesion`→`process_event_transcript`, `procesar_sesiones_pasadas`→`process_past_events`. Inside: rename per field map. Beat schedule key in settings: `'procesar-sesiones-pasadas'`→`'process-past-events'`, task path updated.

## Quiz JSON keys (in cuestionario/quiz JSON and AI prompts)
The AI-generated quiz dicts use keys: `pregunta`→`question`, `opciones`→`options`, `correcta_idx`→`correct_idx`, `explicacion`→`explanation`. IMPORTANT: update both the AI prompt that generates them AND every consumer (serializers, templates, mobile). If unsure whether changing breaks stored data — we wiped the DB, so it is safe to change everywhere consistently.

## SingletonModel API
`get_solo()` → `load()` (used by DisenoGlobal/GlobalDesign, AIConfig, UIDesignTokens).
