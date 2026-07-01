"""Views de cuenta pública (Participante).

Todo se sirve aquí con templates en `public/account/`. Las acciones que
mutan estado (registro, certificados, etc.) tienen forms server-rendered
para evitar la dependencia de JS al inicio.
"""
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from core.models import (
    Certificate,
    Enrollment,
    ProcessingStatus,
    QuizAttempt,
    Participant,
    PasswordResetToken,
    Attendance,
    SessionSummary,
    Event,
)
from public.services import auth as account_auth
from public.services import google_auth as gsignin
from core.services.email import sender as email_sender


# ════════════════════════════════════════════════════════════════
# Auth: login / register / logout
# ════════════════════════════════════════════════════════════════

@require_http_methods(['GET', 'POST'])
def login_view(request):
    if account_auth.get_current_participant(request):
        return redirect('public:account_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next') or request.GET.get('next') or 'public:account_dashboard'

        p = account_auth.authenticate(email, password)
        if not p:
            messages.error(request, 'Email o contraseña incorrectos.')
            return render(request, 'public/account/login.html', {'email': email, 'next': next_url})

        account_auth.login(request, p)
        email_sender.send_login_notification(p, method='Email y contraseña', request=request)
        messages.success(request, f'¡Hola de nuevo, {p.first_name}!')
        if next_url.startswith('/'):
            return redirect(next_url)
        return redirect(next_url)

    return render(request, 'public/account/login.html', {
        'next': request.GET.get('next', ''),
    })


@require_http_methods(['GET', 'POST'])
def register_view(request):
    if account_auth.get_current_participant(request):
        return redirect('public:account_dashboard')

    if request.method == 'POST':
        nombres = request.POST.get('first_name', '').strip()
        apellidos = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        cedula = request.POST.get('national_id', '').strip()
        celular = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        ctx = {
            'form': {'first_name': nombres, 'last_name': apellidos, 'email': email, 'national_id': cedula, 'phone': celular},
        }

        # Validaciones
        if not nombres or not apellidos:
            messages.error(request, 'Nombre y apellido son obligatorios.')
            return render(request, 'public/account/register.html', ctx)
        if not email:
            messages.error(request, 'El email es obligatorio.')
            return render(request, 'public/account/register.html', ctx)
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'public/account/register.html', ctx)
        if len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
            return render(request, 'public/account/register.html', ctx)

        # ¿Ya existe participante con ese email?
        p = Participant.objects.filter(email__iexact=email).first()
        if p:
            if p.has_account:
                messages.error(request, 'Ya existe una cuenta con ese email. Iniciá sesión.')
                return redirect('public:account_login')
            # Existe como guest → upgrade a cuenta
            p.first_name = nombres or p.first_name
            p.last_name = apellidos or p.last_name
            if cedula and not p.national_id:
                p.national_id = cedula
            if celular and not p.phone:
                p.phone = celular
        else:
            p = Participant(
                first_name=nombres, last_name=apellidos, email=email,
                national_id=cedula, phone=celular,
            )

        try:
            p.full_clean(exclude=['password_hash'])
        except Exception as e:
            messages.error(request, f'Datos inválidos: {e}')
            return render(request, 'public/account/register.html', ctx)

        p.set_password(password)
        p.save()
        account_auth.login(request, p)
        email_sender.send_welcome_email(p, request=request)
        messages.success(request, f'¡Bienvenido a CertifAI, {p.first_name}!')
        return redirect('public:account_dashboard')

    return render(request, 'public/account/register.html', {})


def logout_view(request):
    account_auth.logout(request)
    messages.success(request, 'Sesión cerrada.')
    return redirect('public:home')


# ════════════════════════════════════════════════════════════════
# Account Dashboard
# ════════════════════════════════════════════════════════════════

@account_auth.login_required
def dashboard(request):
    import calendar as cal
    from datetime import datetime, timedelta

    p: Participant = request.participant

    certificados = Certificate.objects.filter(
        Q(national_id=p.national_id) if p.national_id else Q(email__iexact=p.email)
    ).order_by('-course_date')

    today = timezone.localdate()
    confirmadas = Enrollment.objects.filter(participant=p)
    asistencias = Attendance.objects.filter(participant=p)
    eventos_inscrito_ids = set(confirmadas.values_list('event_id', flat=True))
    eventos_asistido_ids = set(asistencias.values_list('event_id', flat=True))

    # Total horas certificadas (suma de horas de todos los certificados)
    total_horas = sum(c.hours or 0 for c in certificados)

    # ── Próximo evento (el más cercano donde está inscrito) ────────
    next_event = (Event.objects
        .filter(is_active=True, id__in=eventos_inscrito_ids, date__gte=today)
        .order_by('date', 'start_time')
        .first())
    next_event_dt_iso = None
    if next_event:
        ne_dt = datetime.combine(next_event.date, next_event.start_time)
        next_event_dt_iso = ne_dt.isoformat()

    eventos_proximos = (Event.objects
        .filter(is_active=True, id__in=eventos_inscrito_ids, date__gte=today)
        .prefetch_related('speakers')
        .order_by('date', 'start_time')[:3])

    # Recomendaciones — futuros activos sin inscripción
    eventos_recomendados = (Event.objects
        .filter(is_active=True, date__gte=today)
        .exclude(id__in=eventos_inscrito_ids)
        .prefetch_related('speakers')
        .order_by('date', 'start_time')[:6])

    # ── Calendario del mes actual ───────────────────────────────────
    cal.setfirstweekday(cal.MONDAY)
    year, month = today.year, today.month
    month_matrix = cal.monthcalendar(year, month)  # lista de semanas con días (0 = vacío)

    # Eventos del mes (todos los activos para mostrarlos en el calendar) + status del user
    first_of_month = today.replace(day=1)
    last_day = cal.monthrange(year, month)[1]
    last_of_month = today.replace(day=last_day)

    sesiones_mes = Event.objects.filter(
        is_active=True,
        date__gte=first_of_month,
        date__lte=last_of_month,
    ).order_by('date', 'start_time')

    cal_days = {}  # day_int → {'inscrito': N, 'disponible': N, 'asisti': N}
    for s in sesiones_mes:
        d = s.date.day
        slot = cal_days.setdefault(d, {'inscrito': 0, 'disponible': 0, 'asisti': 0, 'eventos': []})
        slot['eventos'].append({
            'id': s.id,
            'titulo': s.title or s.day_of_week,
            'hora': s.start_time.strftime('%H:%M'),
            'es_virtual': s.is_virtual,
        })
        if s.id in eventos_asistido_ids:
            slot['asisti'] += 1
        elif s.id in eventos_inscrito_ids:
            slot['inscrito'] += 1
        else:
            slot['disponible'] += 1

    # Build calendar weeks structure for the template
    cal_weeks = []
    for week in month_matrix:
        cal_week = []
        for day in week:
            if day == 0:
                cal_week.append({'day': None})
            else:
                info = cal_days.get(day, {})
                cal_week.append({
                    'day': day,
                    'is_today': (day == today.day),
                    'is_past': day < today.day,
                    'has_inscrito': info.get('inscrito', 0) > 0,
                    'has_asisti': info.get('asisti', 0) > 0,
                    'has_disponible': info.get('disponible', 0) > 0,
                    'eventos': info.get('eventos', []),
                })
        cal_weeks.append(cal_week)

    meses_es = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    # ── Actividad reciente (últimos 5 eventos: certificados + inscripciones + asistencias) ──
    from datetime import date as _date_cls
    activity = []
    for c in certificados[:3]:
        if not c.course_date:
            continue  # certificados sin fecha quedan fuera del feed
        activity.append({
            'tipo': 'certificado',
            'titulo': c.course,
            'fecha': c.course_date,
            'icono': 'fa-certificate',
            'color': 'success',
        })
    for s in eventos_proximos[:2]:
        if not s.date:
            continue
        activity.append({
            'tipo': 'inscrito',
            'titulo': s.title or s.day_of_week,
            'fecha': s.date,
            'icono': 'fa-bookmark',
            'color': 'brand',
        })
    activity.sort(key=lambda x: x['fecha'] or _date_cls.min, reverse=True)
    activity = activity[:5]

    # Día resaltado por deep-link desde correos: ?day=YYYY-MM-DD
    highlight_day = None
    day_param = request.GET.get('day', '').strip()
    if day_param:
        try:
            from datetime import date as _date
            parsed = _date.fromisoformat(day_param)
            if parsed.month == month and parsed.year == year:
                highlight_day = parsed.day
        except ValueError:
            pass

    return render(request, 'public/account/dashboard.html', {
        'p': p,
        'today': today,
        'certificados_count': certificados.count(),
        'total_horas': total_horas,
        'eventos_inscrito_count': len(eventos_inscrito_ids),
        'eventos_asistido_count': len(eventos_asistido_ids),
        'certificados_recientes': certificados[:3],
        'eventos_proximos': eventos_proximos,
        'eventos_recomendados': eventos_recomendados,
        # Calendar
        'cal_weeks': cal_weeks,
        'cal_year': year,
        'cal_month_name': meses_es[month - 1],
        'highlight_day': highlight_day,
        # Próximo evento + countdown
        'next_event': next_event,
        'next_event_dt_iso': next_event_dt_iso,
        # Actividad
        'activity': activity,
    })


# ════════════════════════════════════════════════════════════════
# Mis Certificados
# ════════════════════════════════════════════════════════════════

@account_auth.login_required
def certificados_view(request):
    p: Participant = request.participant
    q = request.GET.get('q', '').strip()

    qs = Certificate.objects.filter(
        Q(national_id=p.national_id) if p.national_id else Q(email__iexact=p.email)
    ).select_related('batch').order_by('-course_date')

    if q:
        qs = qs.filter(Q(course__icontains=q) | Q(batch__name__icontains=q))

    return render(request, 'public/account/certificados.html', {
        'p': p,
        'certificados': qs,
        'total': qs.count(),
        'q': q,
    })


# ════════════════════════════════════════════════════════════════
# Mis Eventos (tabs: registrado · asistido · disponibles)
# ════════════════════════════════════════════════════════════════

@account_auth.login_required
def eventos_view(request):
    p: Participant = request.participant
    tab = request.GET.get('tab', 'mios')  # mios | disponibles
    today = timezone.localdate()

    confirmados_ids = set(Enrollment.objects.filter(participant=p).values_list('event_id', flat=True))
    asistidos_ids = set(Attendance.objects.filter(participant=p).values_list('event_id', flat=True))
    mis_ids = confirmados_ids | asistidos_ids

    if tab == 'disponibles':
        eventos = (Event.objects
            .filter(is_active=True, date__gte=today)
            .exclude(id__in=mis_ids)
            .prefetch_related('speakers')
            .order_by('date', 'start_time'))
    else:
        eventos = (Event.objects
            .filter(id__in=mis_ids)
            .prefetch_related('speakers')
            .order_by('-date', '-start_time'))

    # Sesiones con resumen IA listo (para mostrar el badge "Betto" en la card)
    resumen_listo_ids = set(
        SessionSummary.objects
        .filter(status=ProcessingStatus.READY, event_id__in=[e.id for e in eventos])
        .values_list('event_id', flat=True)
    )

    # Anotar estado de cada evento para el participante
    eventos_data = []
    for e in eventos:
        status = 'disponible'
        if e.id in asistidos_ids:
            status = 'asisti'
        elif e.id in confirmados_ids:
            if e.date < today:
                status = 'no_asisti'
            else:
                status = 'inscrito'
        eventos_data.append({
            'e': e,
            'status': status,
            'has_resumen': e.id in resumen_listo_ids,
        })

    return render(request, 'public/account/eventos.html', {
        'p': p,
        'tab': tab,
        'eventos_data': eventos_data,
        'count_mios': len(mis_ids),
        'count_disponibles': Event.objects.filter(is_active=True, date__gte=today).exclude(id__in=mis_ids).count(),
    })


@account_auth.login_required
def perfil_view(request):
    p: Participant = request.participant
    if request.method == 'POST':
        p.first_name = request.POST.get('nombres', p.first_name).strip()
        p.last_name = request.POST.get('apellidos', p.last_name).strip()
        cedula_in = request.POST.get('cedula', '').strip()
        if cedula_in and cedula_in != p.national_id:
            p.national_id = cedula_in
        p.phone = request.POST.get('celular', p.phone).strip()
        new_pwd = request.POST.get('new_password', '')
        if new_pwd:
            if len(new_pwd) < 6:
                messages.error(request, 'La nueva contraseña debe tener al menos 6 caracteres.')
                return render(request, 'public/account/perfil.html', {'p': p})
            p.set_password(new_pwd)
        if 'avatar' in request.FILES:
            p.avatar = request.FILES['avatar']
        try:
            p.full_clean(exclude=['password_hash'])
        except Exception as e:
            messages.error(request, f'Datos inválidos: {e}')
            return render(request, 'public/account/perfil.html', {'p': p})
        p.save()
        messages.success(request, 'Perfil actualizado.')
        return redirect('public:account_perfil')

    return render(request, 'public/account/perfil.html', {'p': p})


# ════════════════════════════════════════════════════════════════
# Acción: registrarse a un evento desde la cuenta (1 click)
# ════════════════════════════════════════════════════════════════

@account_auth.login_required
def evento_resumen_view(request, sesion_id: int):
    """Pantalla web del resumen IA del evento (Betto).

    Visible para cualquier participante que se haya INSCRITO (haya asistido o
    no). Idea: si al participante se le fue la luz o tuvo problemas técnicos,
    igual puede ponerse al día con el resumen + ver la grabación.
    Muestra resumen Markdown, puntos clave, próximos pasos y cuestionario.
    """
    p: Participant = request.participant
    try:
        sesion = Event.objects.get(pk=sesion_id, is_active=True)
    except Event.DoesNotExist:
        raise Http404

    # Acceso para inscritos (cualquier estado: asistió, no asistió, confirmado)
    inscrito = Enrollment.objects.filter(participant=p, event=sesion).exists()
    asistio  = Attendance.objects.filter(participant=p, event=sesion).exists()
    if not (inscrito or asistio):
        messages.error(request, 'Solo podés ver el resumen si te inscribiste al evento.')
        return redirect('public:account_eventos')

    resumen = SessionSummary.objects.filter(event=sesion).first()

    # Buscar grabación en Drive (lazy, no la persistimos aún)
    recording = None
    if resumen and resumen.status == ProcessingStatus.READY:
        try:
            from core.services.meet.drive_client import find_recording_for_session
            recording = find_recording_for_session(sesion)
        except Exception:
            recording = None  # silencioso — el resumen no depende del video

    # Intentos previos del cuestionario (este participante en esta sesión)
    intentos = list(QuizAttempt.objects.filter(participant=p, event=sesion))
    mejor_intento = max(intentos, key=lambda x: x.correct, default=None)
    intentos_disponibles = max(0, QuizAttempt.MAX_ATTEMPTS - len(intentos))

    return render(request, 'public/account/evento_resumen.html', {
        'p': p,
        'event': sesion,
        'summary': resumen,
        'recording': recording,
        'asistio': asistio,
        'attempts': intentos,
        'best_attempt': mejor_intento,
        'attempts_available': intentos_disponibles,
        'max_attempts': QuizAttempt.MAX_ATTEMPTS,
        'is_ready': resumen.status == ProcessingStatus.READY if resumen else False,
        'is_processing': (
            resumen.status in (
                ProcessingStatus.PENDING,
                ProcessingStatus.SEARCHING,
                ProcessingStatus.PROCESSING,
            ) if resumen else False
        ),
    })


@account_auth.login_required
def evento_resumen_pdf_view(request, sesion_id: int):
    """Descarga el resumen IA como PDF profesional.

    Acceso: cualquier participante inscrito (o que asistió). Genera el PDF
    on-the-fly usando `core.services.pdf.resumen_pdf.generar_resumen_pdf`.
    """
    p: Participant = request.participant
    try:
        sesion = Event.objects.get(pk=sesion_id, is_active=True)
    except Event.DoesNotExist:
        raise Http404

    inscrito = Enrollment.objects.filter(participant=p, event=sesion).exists()
    asistio  = Attendance.objects.filter(participant=p, event=sesion).exists()
    if not (inscrito or asistio):
        messages.error(request, 'Solo podés descargar el resumen si te inscribiste al evento.')
        return redirect('public:account_eventos')

    resumen = SessionSummary.objects.filter(event=sesion).first()
    if not resumen or resumen.status != ProcessingStatus.READY:
        messages.info(request, 'El resumen aún no está listo. Volvé en unos minutos.')
        return redirect('public:account_evento_resumen', sesion_id=sesion.id)

    from core.services.pdf.resumen_pdf import generar_resumen_pdf
    pdf_bytes = generar_resumen_pdf(resumen)

    titulo_slug = slugify(sesion.title or sesion.day_of_week or 'evento')[:50] or 'resumen'
    fecha_slug = sesion.date.strftime('%Y-%m-%d') if sesion.date else 'sf'
    filename = f'Resumen-Betto-{titulo_slug}-{fecha_slug}.pdf'

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['Content-Length'] = len(pdf_bytes)
    return response


@account_auth.login_required
def evento_cuestionario_view(request, sesion_id: int):
    """Pantalla inmersiva del cuestionario IA, estilo Quizizz/Wayground.

    Acceso: cualquier inscrito al evento. Si no hay cuestionario o el
    resumen aún no está LISTO, redirige al resumen para mostrar el estado.
    """
    p: Participant = request.participant
    try:
        sesion = Event.objects.get(pk=sesion_id, is_active=True)
    except Event.DoesNotExist:
        raise Http404

    inscrito = Enrollment.objects.filter(participant=p, event=sesion).exists()
    asistio  = Attendance.objects.filter(participant=p, event=sesion).exists()
    if not (inscrito or asistio):
        messages.error(request, 'Solo podés acceder al cuestionario si te inscribiste al evento.')
        return redirect('public:account_eventos')

    if not sesion.quiz_enabled:
        messages.info(request, 'Este evento no tiene cuestionario.')
        return redirect('public:account_evento_resumen', sesion_id=sesion.id)

    resumen = SessionSummary.objects.filter(event=sesion).first()
    if not resumen or resumen.status != ProcessingStatus.READY or not resumen.quiz:
        return redirect('public:account_evento_resumen', sesion_id=sesion.id)

    # Bloqueo de intentos: máximo MAX_ATTEMPTS por participante por sesión
    intentos_count = QuizAttempt.objects.filter(participant=p, event=sesion).count()
    if intentos_count >= QuizAttempt.MAX_ATTEMPTS:
        messages.info(
            request,
            f'Ya completaste tus {QuizAttempt.MAX_ATTEMPTS} intentos del cuestionario. '
            'Mirá tus resultados acá abajo.',
        )
        return redirect('public:account_evento_resumen', sesion_id=sesion.id)

    return render(request, 'public/account/evento_cuestionario.html', {
        'p': p,
        'event': sesion,
        'summary': resumen,
        'attempt_number': intentos_count + 1,
        'attempts_remaining_after': QuizAttempt.MAX_ATTEMPTS - (intentos_count + 1),
    })


@account_auth.login_required
@require_POST
def evento_cuestionario_submit(request, sesion_id: int):
    """Guarda el resultado de un intento del cuestionario.

    Body JSON: { respuestas: [int|null], tiempo_total_seg: int }
    Devuelve: { ok, intento_id, correctas, total, intentos_restantes }
    """
    import json
    p: Participant = request.participant
    try:
        sesion = Event.objects.get(pk=sesion_id, is_active=True)
    except Event.DoesNotExist:
        raise Http404

    inscrito = Enrollment.objects.filter(participant=p, event=sesion).exists()
    asistio  = Attendance.objects.filter(participant=p, event=sesion).exists()
    if not (inscrito or asistio):
        return JsonResponse({'ok': False, 'error': 'Sin acceso al cuestionario.'}, status=403)

    resumen = SessionSummary.objects.filter(event=sesion).first()
    if not resumen or resumen.status != ProcessingStatus.READY or not resumen.quiz:
        return JsonResponse({'ok': False, 'error': 'Cuestionario no disponible.'}, status=400)

    intentos_count = QuizAttempt.objects.filter(participant=p, event=sesion).count()
    if intentos_count >= QuizAttempt.MAX_ATTEMPTS:
        return JsonResponse({
            'ok': False,
            'error': f'Ya alcanzaste el máximo de {QuizAttempt.MAX_ATTEMPTS} intentos.',
        }, status=409)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido.'}, status=400)

    respuestas = body.get('respuestas') or []
    tiempo_total = int(body.get('tiempo_total_seg') or 0)

    preguntas = resumen.quiz
    total = len(preguntas)
    correctas = 0
    for i, q in enumerate(preguntas):
        if i < len(respuestas) and respuestas[i] is not None:
            if respuestas[i] == q.get('correct_idx'):
                correctas += 1

    intento = QuizAttempt.objects.create(
        participant=p,
        event=sesion,
        correct=correctas,
        total=total,
        total_time_seconds=tiempo_total,
        answers=respuestas,
    )
    intentos_restantes = QuizAttempt.MAX_ATTEMPTS - (intentos_count + 1)
    return JsonResponse({
        'ok': True,
        'intento_id': intento.id,
        'correctas': correctas,
        'total': total,
        'porcentaje': intento.percentage,
        'intentos_restantes': intentos_restantes,
    })


@account_auth.login_required
@require_POST
def evento_inscribir(request, sesion_id: int):
    p: Participant = request.participant
    try:
        sesion = Event.objects.get(pk=sesion_id, is_active=True)
    except Event.DoesNotExist:
        raise Http404
    _, created = Enrollment.objects.get_or_create(participant=p, event=sesion)
    if created:
        email_sender.send_event_inscription(p, sesion, request=request)
    messages.success(request, f'Te inscribiste a "{sesion.title or sesion.day_of_week}"')
    return redirect(request.META.get('HTTP_REFERER') or 'public:account_eventos')


# ════════════════════════════════════════════════════════════════
# Escanear QR desde la cuenta (web — usa cámara del navegador)
# ════════════════════════════════════════════════════════════════

@account_auth.login_required
def escanear_view(request):
    """Pantalla con la cámara del navegador para escanear el QR de un evento."""
    return render(request, 'public/account/escanear.html')


@account_auth.login_required
@require_POST
def escanear_registrar(request):
    """Recibe el codigo_qr (de un POST JSON o form) y registra asistencia.

    Idempotente: si ya estaba registrado, devuelve `already_registered=True`.
    Si nunca se inscribió, lo inscribe automáticamente al escanear.
    """
    import json
    p: Participant = request.participant

    # Aceptar tanto JSON como form
    codigo_qr = ''
    if request.content_type and 'json' in request.content_type:
        try:
            data = json.loads(request.body or b'{}')
            codigo_qr = (data.get('codigo_qr') or '').strip()
        except Exception:
            return JsonResponse({'ok': False, 'error': 'Body inválido.'}, status=400)
    else:
        codigo_qr = (request.POST.get('codigo_qr') or '').strip()

    if not codigo_qr:
        return JsonResponse({'ok': False, 'error': 'Falta el código QR.'}, status=400)

    # Si vino una URL completa, extraemos el último segmento
    if '/' in codigo_qr:
        parts = [s for s in codigo_qr.rstrip('/').split('/') if s]
        if parts:
            codigo_qr = parts[-1]

    try:
        sesion = Event.objects.get(qr_code=codigo_qr, is_active=True)
    except Event.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'QR inválido o sesión no activa.'}, status=404)

    # Inscribir al vuelo si no estaba inscrito
    Enrollment.objects.get_or_create(participant=p, event=sesion)

    # Registrar asistencia (unique constraint asegura idempotencia)
    ip = (
        request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
        or request.META.get('REMOTE_ADDR')
    )
    _, created = Attendance.objects.get_or_create(
        participant=p, event=sesion,
        defaults={'ip_address': ip},
    )
    return JsonResponse({
        'ok': True,
        'created': created,
        'already_registered': not created,
        'sesion_titulo': sesion.title or sesion.day_of_week,
        'sesion_fecha':  sesion.date.strftime('%Y-%m-%d'),
        'sesion_hora':   sesion.start_time.strftime('%H:%M'),
    })


# ════════════════════════════════════════════════════════════════
# Landing pública (rediseñada) — datos para el carousel/swiper
# ════════════════════════════════════════════════════════════════

def home(request):
    today = timezone.localdate()
    eventos = (Event.objects
        .filter(is_active=True, date__gte=today)
        .order_by('date', 'start_time'))

    # 5 destacados para el hero (los más próximos)
    eventos_hero = list(eventos[:5])
    # 9 para el grid
    eventos_grid = list(eventos[:9])

    return render(request, 'public/home.html', {
        'eventos_hero': eventos_hero,
        'eventos_grid': eventos_grid,
        'total_eventos': eventos.count(),
    })


# ════════════════════════════════════════════════════════════════
# Google Sign-In (login con cuenta Google)
# ════════════════════════════════════════════════════════════════

def google_signin_start(request):
    """Inicia el flujo OAuth — redirige a la pantalla de consent de Google."""
    if not getattr(settings, 'GOOGLE_CLIENT_ID', None):
        messages.error(request, 'Google Sign-In no está configurado.')
        return redirect('public:account_login')

    redirect_uri = request.build_absolute_uri('/cuenta/google/callback/')
    flow = gsignin.build_signin_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type='online',
        include_granted_scopes='true',
        prompt='select_account',
    )
    request.session['gsignin_state'] = state
    # PKCE: guardar code_verifier — el callback necesita restaurarlo
    request.session['gsignin_code_verifier'] = flow.code_verifier
    request.session['gsignin_next'] = request.GET.get('next', '')
    return redirect(auth_url)


def google_signin_callback(request):
    """Recibe el code de Google, valida el id_token y loguea/crea participante."""
    error = request.GET.get('error')
    if error:
        messages.error(request, f'Google rechazó la autorización: {error}')
        return redirect('public:account_login')

    state = request.session.pop('gsignin_state', None)
    code_verifier = request.session.pop('gsignin_code_verifier', None)
    next_url = request.session.pop('gsignin_next', '')
    code = request.GET.get('code')
    if not code:
        messages.error(request, 'Google no devolvió código de autorización.')
        return redirect('public:account_login')

    redirect_uri = request.build_absolute_uri('/cuenta/google/callback/')

    try:
        flow = gsignin.build_signin_flow(redirect_uri, state=state)
        if code_verifier:
            flow.code_verifier = code_verifier  # restaurar PKCE verifier
        flow.fetch_token(code=code)
        creds = flow.credentials
        info = gsignin.fetch_userinfo_from_idtoken(creds.id_token)
    except Exception as exc:
        messages.error(request, f'Error procesando inicio con Google: {exc}')
        return redirect('public:account_login')

    email = (info.get('email') or '').strip().lower()
    if not email:
        messages.error(request, 'Google no devolvió email.')
        return redirect('public:account_login')

    # Buscar o crear el participante por email
    p = Participant.objects.filter(email__iexact=email).first()
    if not p:
        p = Participant(
            email=email,
            first_name=info.get('given_name') or email.split('@')[0],
            last_name=info.get('family_name') or '',
        )
        p.save()
        created = True
    else:
        if not p.first_name and info.get('given_name'):
            p.first_name = info['given_name']
        if not p.last_name and info.get('family_name'):
            p.last_name = info['family_name']
        p.save()
        created = False

    account_auth.login(request, p)
    if created:
        email_sender.send_welcome_email(p, request=request)
    else:
        email_sender.send_login_notification(p, method='Google', request=request)

    messages.success(
        request,
        f'¡Hola {p.first_name}! ' + ('Tu cuenta fue creada con Google.' if created else 'Iniciaste sesión con Google.')
    )

    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('public:account_dashboard')


# ════════════════════════════════════════════════════════════════
# Recuperación de contraseña
# ════════════════════════════════════════════════════════════════
# Flujo:
#   1. /cuenta/recuperar/         -> usuario ingresa email (request)
#   2. /cuenta/recuperar/enviado/ -> "revisa tu correo" + input para código
#   3a. magic link en correo -> /cuenta/recuperar/r/<uuid>/ -> verifica + sesión efímera
#   3b. código manual -> POST a /cuenta/recuperar/codigo/   -> verifica + sesión efímera
#   4. /cuenta/recuperar/nueva/   -> formulario de nueva contraseña (requiere paso 3)
#
# La "sesión efímera" es request.session['pwd_reset_verified_participant_id']
# fijado en el paso 3 y consumido en el paso 4 (luego se borra).

PWD_RESET_SESSION_KEY = 'pwd_reset_verified_participant_id'
PWD_RESET_REQUEST_KEY = 'pwd_reset_request_id'  # para polling cross-device


def _client_ip(request) -> str:
    fwd = request.META.get('HTTP_X_FORWARDED_FOR')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


@require_http_methods(['GET', 'POST'])
def password_reset_request(request):
    """Paso 1: pide el email y dispara el envío del correo."""
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        # Nunca revelar si el email existe (evita enumeración).
        # Siempre redirigir a la página "enviado".
        try:
            participant = Participant.objects.get(email__iexact=email)
            if participant.has_account:
                token, code = PasswordResetToken.issue(
                    participant,
                    ip=_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                )
                site = f'{request.scheme}://{request.get_host()}'
                reset_url = f'{site}/cuenta/recuperar/r/{token.token}/'
                email_sender.send_password_reset_email(
                    participant,
                    reset_url=reset_url,
                    code=code,
                    request=request,
                )
                request.session[PWD_RESET_REQUEST_KEY] = str(token.token)
        except Participant.DoesNotExist:
            # Igual seguimos al "enviado" para no revelar existencia.
            pass

        return redirect('public:account_password_reset_sent')

    return render(request, 'public/account/password_reset_request.html')


@require_http_methods(['GET'])
def password_reset_sent(request):
    """Paso 2: pantalla 'revisa tu correo' con entrada para el código de 6 dígitos."""
    return render(request, 'public/account/password_reset_sent.html', {
        'request_id': request.session.get(PWD_RESET_REQUEST_KEY, ''),
    })


@require_http_methods(['GET'])
def password_reset_link(request, token: str):
    """Paso 3a: el usuario hace clic en el magic link del correo."""
    try:
        prt = PasswordResetToken.objects.select_related('participant').get(token=token)
    except (PasswordResetToken.DoesNotExist, ValueError, Exception):
        messages.error(request, 'Este enlace no es válido o ya fue usado.')
        return redirect('public:account_password_reset_request')

    if not prt.is_active:
        messages.error(request, 'Este enlace expiró o ya fue usado. Pídelo de nuevo.')
        return redirect('public:account_password_reset_request')

    prt.consume()
    request.session[PWD_RESET_SESSION_KEY] = prt.participant_id
    return redirect('public:account_password_reset_new')


@require_POST
def password_reset_verify_code(request):
    """Paso 3b: el usuario tipea el código de 6 dígitos."""
    code = (request.POST.get('code') or '').strip().replace(' ', '').replace('-', '')

    # Buscar tokens activos cuyo code_hash coincida
    candidates = PasswordResetToken.objects.filter(
        used_at__isnull=True, expires_at__gt=timezone.now(),
    ).select_related('participant')

    matched = None
    for prt in candidates:
        if prt.matches_code(code):
            matched = prt
            break

    if matched is None:
        messages.error(request, 'Código inválido o expirado. Pídelo de nuevo si pasaron más de 15 minutos.')
        return redirect('public:account_password_reset_sent')

    matched.consume()
    request.session[PWD_RESET_SESSION_KEY] = matched.participant_id
    return redirect('public:account_password_reset_new')


@require_http_methods(['GET'])
def password_reset_status(request):
    """Endpoint de polling: ¿el token del request actual ya fue usado en otro dispositivo?

    Lo consulta la página /enviado/ cada N segundos para auto-avanzar cuando
    el usuario hace clic en el magic link desde el celular.
    """
    rid = request.session.get(PWD_RESET_REQUEST_KEY)
    if not rid:
        return JsonResponse({'status': 'idle'})
    try:
        prt = PasswordResetToken.objects.get(token=rid)
    except (PasswordResetToken.DoesNotExist, ValueError):
        return JsonResponse({'status': 'unknown'})
    if prt.used_at:
        return JsonResponse({'status': 'verified'})
    if timezone.now() >= prt.expires_at:
        return JsonResponse({'status': 'expired'})
    return JsonResponse({'status': 'pending'})


@require_http_methods(['GET', 'POST'])
def password_reset_new(request):
    """Paso 4: el usuario establece su nueva contraseña."""
    pid = request.session.get(PWD_RESET_SESSION_KEY)
    if not pid:
        messages.info(request, 'Tu verificación expiró. Inicia el proceso nuevamente.')
        return redirect('public:account_password_reset_request')

    try:
        participant = Participant.objects.get(pk=pid)
    except Participant.DoesNotExist:
        request.session.pop(PWD_RESET_SESSION_KEY, None)
        return redirect('public:account_password_reset_request')

    if request.method == 'POST':
        pw1 = request.POST.get('password', '')
        pw2 = request.POST.get('password_confirm', '')
        if len(pw1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif pw1 != pw2:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            participant.set_password(pw1)
            participant.save(update_fields=['password_hash'])
            # Limpiar la sesión de reset
            request.session.pop(PWD_RESET_SESSION_KEY, None)
            request.session.pop(PWD_RESET_REQUEST_KEY, None)
            messages.success(request, '¡Listo! Tu contraseña fue actualizada. Inicia sesión.')
            return redirect('public:account_login')

    return render(request, 'public/account/password_reset_new.html', {
        'participant': participant,
    })
