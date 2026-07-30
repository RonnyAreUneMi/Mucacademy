from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import AccessRequest, User
from core.security.decorators import module_required
from ._shared import admin_required, superadmin_required, _log_audit

class CustomLoginView(DjangoLoginView):
    """Custom login view that checks for pending access requests"""
    template_name = 'panel/auth/login.html'
    redirect_authenticated_user = False  # We handle redirect manually
    
    def get(self, request, *args, **kwargs):
        # If user is already authenticated, route them properly
        if request.user.is_authenticated:
            return self._route_authenticated_user(request.user)
        return super().get(request, *args, **kwargs)
    
    def _route_authenticated_user(self, user):
        """Route an authenticated user to the correct page based on their status."""
        # Check if user has pending access request
        try:
            AccessRequest.objects.get(created_user=user, status='pending')
            return redirect('panel:mi_estado')
        except AccessRequest.DoesNotExist:
            pass

        # Check if user is active admin
        if user.is_active and user.role in ['admin', 'superadmin']:
            return redirect('panel:dashboard')
        
        # Inactive user - send to mi_estado
        return redirect('panel:mi_estado')
    
    def form_valid(self, form):
        from django.contrib.auth import login
        user = form.get_user()

        # Always log the user in first
        login(self.request, user, backend='admin_panel.backends.EmailBackend')

        # Route them to the correct page
        return self._route_authenticated_user(user)

    def form_invalid(self, form):
        # Limpiamos los errores genéricos del form y mostramos un mensaje custom
        form.errors.clear()
        if not any(m.level_tag == 'error' for m in messages.get_messages(self.request)):
            messages.error(
                self.request,
                "Has ingresado mal tu usuario o contraseña. Inténtalo de nuevo."
            )
        return super().form_invalid(form)


def register(request):
    """Shell del formulario. Submit va a /api/v1/auth/register/ via fetch."""
    if request.user.is_authenticated:
        if request.user.is_active and request.user.role in ['admin', 'superadmin']:
            return redirect('panel:dashboard')
        return redirect('panel:mi_estado')

    from core.models import FACULTY_CHOICES
    return render(request, 'panel/auth/register.html', {
        'facultades_choices': FACULTY_CHOICES,
    })


def solicitud_pendiente(request, id):
    """Página de solicitud pendiente - redirige a mi_estado si está autenticado"""
    if request.user.is_authenticated:
        return redirect('panel:mi_estado')
    
    solicitud = get_object_or_404(AccessRequest, id=id)

    # Si está aprobada, redirigir a login
    if solicitud.status == 'approved':
        messages.success(request, 'Tu solicitud fue aprobada. Inicia sesión con tu correo y contraseña.')
        return redirect('panel:login')

    # Si está rechazada, mostrar motivo
    if solicitud.status == 'rejected':
        return render(request, 'panel/auth/solicitud_rechazada.html', {'solicitud': solicitud})
    
    # Si está pendiente, redirigir a login para que inicie sesión
    messages.info(request, 'Inicia sesión con tu correo y contraseña para ver el estado de tu solicitud.')
    return redirect('panel:login')


@login_required
def mi_estado(request):
    """Página de estado para usuarios pendientes de aprobación"""
    user = request.user
    
    # Si el usuario está activo y es admin, redirigir al dashboard
    if user.is_active and user.role in ['admin', 'superadmin']:
        return redirect('panel:dashboard')

    # Buscar la solicitud del usuario
    solicitud = None
    estado = 'pending'
    try:
        solicitud = AccessRequest.objects.get(created_user=user)
        estado = solicitud.status
    except AccessRequest.DoesNotExist:
        # Si no tiene solicitud pero no está activo, mostrar mensaje genérico
        if not user.is_active:
            estado = 'deactivated'

    # Si la solicitud fue aprobada, verificar si el usuario está activo
    if estado == 'approved' and user.is_active:
        return redirect('panel:dashboard')
    
    context = {
        'solicitud': solicitud,
        'estado': estado,
        'user': user,
    }
    return render(request, 'panel/auth/mi_estado.html', context)


@admin_required
@module_required('solicitudes')
def solicitudes_pendientes(request):
    """Admin view: lista de solicitudes de acceso pendientes"""
    estado_filter = request.GET.get('estado', 'pending')

    solicitudes = AccessRequest.objects.all().order_by('-requested_at')

    if estado_filter == 'pending':
        solicitudes = solicitudes.filter(status='pending')
    elif estado_filter == 'approved':
        solicitudes = solicitudes.filter(status='approved')
    elif estado_filter == 'rejected':
        solicitudes = solicitudes.filter(status='rejected')

    pendientes_count = AccessRequest.objects.filter(status='pending').count()
    aprobadas_count = AccessRequest.objects.filter(status='approved').count()
    rechazadas_count = AccessRequest.objects.filter(status='rejected').count()
    
    context = {
        'solicitudes': solicitudes,
        'estado_filter': estado_filter,
        'pendientes_count': pendientes_count,
        'aprobadas_count': aprobadas_count,
        'rechazadas_count': rechazadas_count,
    }
    return render(request, 'panel/solicitudes/pendientes.html', context)


@admin_required
@require_http_methods(["POST"])
@module_required('solicitudes', 'editar')
def aprobar_solicitud(request, id):
    """Admin action: aprobar una solicitud de acceso - activa el usuario existente"""
    solicitud = get_object_or_404(AccessRequest, id=id)

    if solicitud.status not in ['pending', 'rejected']:
        messages.error(request, 'Esta solicitud no puede ser procesada.')
        return redirect('panel:solicitudes_pendientes')

    # Limpiar motivo de rechazo si existía
    if solicitud.status == 'rejected':
        solicitud.rejection_reason = ''

    try:
        if solicitud.created_user:
            # Activar el usuario existente (creado durante el registro)
            usuario = solicitud.created_user
            usuario.is_active = True
            usuario.save(update_fields=['is_active'])
            nombre_usuario = usuario.username
        else:
            # Solicitud legacy sin usuario vinculado - crear uno nuevo
            nombre_usuario = solicitud.email.split('@')[0]
            base_username = nombre_usuario
            counter = 1
            while User.objects.filter(username=nombre_usuario).exists():
                nombre_usuario = f"{base_username}{counter}"
                counter += 1

            usuario = User.objects.create_user(
                username=nombre_usuario,
                email=solicitud.email,
                first_name=solicitud.first_name,
                last_name=solicitud.last_name,
                phone=solicitud.phone,
                faculty=solicitud.faculty,
                role='professor',   # los nuevos son profesores; un superadmin los promueve si hace falta
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
            solicitud.created_user = usuario

        # Actualizar solicitud
        solicitud.status = 'approved'
        solicitud.approved_by = request.user
        solicitud.responded_at = timezone.now()
        solicitud.save()
        
        # Log de auditoría
        _log_audit(request.user, 'APPROVE',
                  f'Solicitud de {solicitud.email} aprobada. Usuario {nombre_usuario} activado.')
        
        messages.success(request, f'Solicitud aprobada. Usuario activado: {nombre_usuario}')
    except Exception as e:
        messages.error(request, f'Error al procesar la solicitud: {str(e)}')
    
    return redirect('panel:solicitudes_pendientes')


@admin_required
@require_http_methods(["GET", "POST"])
@module_required('solicitudes', 'editar')
def rechazar_solicitud(request, id):
    """Admin action: rechazar una solicitud de acceso"""
    solicitud = get_object_or_404(AccessRequest, id=id)

    if solicitud.status != 'pending':
        messages.error(request, 'Esta solicitud ya ha sido procesada.')
        return redirect('panel:solicitudes_pendientes')

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')

        solicitud.status = 'rejected'
        solicitud.rejection_reason = motivo
        solicitud.approved_by = request.user
        solicitud.responded_at = timezone.now()
        solicitud.save()
        
        _log_audit(request.user, 'REJECT',
                  f'Solicitud de {solicitud.email} rechazada. Motivo: {motivo}')
        
        messages.success(request, f'Solicitud rechazada: {solicitud.email}')
        return redirect('panel:solicitudes_pendientes')
    
    return render(request, 'panel/solicitudes/rechazar.html', {'solicitud': solicitud})


