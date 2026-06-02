"""Register endpoint: crea User (inactivo) + AccessRequest pendiente."""
from django.db import transaction
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import FACULTY_CHOICES, AccessRequest, User


class RegisterInputSerializer(serializers.Serializer):
    nombres = serializers.CharField(max_length=100)
    apellidos = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    facultad = serializers.ChoiceField(choices=[c[0] for c in FACULTY_CHOICES])
    password = serializers.CharField(min_length=6, write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_telefono(self, value):
        if not value:
            return value
        value = value.replace(' ', '').replace('-', '')
        if not value.isdigit():
            raise serializers.ValidationError('El teléfono solo debe contener números.')
        if len(value) != 10:
            raise serializers.ValidationError('El número de teléfono debe tener exactamente 10 dígitos.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con ese email.')
        if AccessRequest.objects.filter(email__iexact=value, status='pending').exists():
            raise serializers.ValidationError('Ya hay una solicitud pendiente con ese email.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Las contraseñas no coinciden.'})
        return attrs


class RegisterView(APIView):
    """POST /api/v1/auth/register/ → crea User inactivo + solicitud pendiente."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RegisterInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        with transaction.atomic():
            usuario = User.objects.create(
                username=data['email'],
                email=data['email'],
                first_name=data['nombres'],
                last_name=data['apellidos'],
                role='admin',
                faculty=data['facultad'],
                phone=data.get('telefono', ''),
                is_active=False,
                is_staff=False,
                is_superuser=False,
            )
            usuario.set_password(data['password'])
            usuario.save()

            solicitud = AccessRequest.objects.create(
                first_name=data['nombres'],
                last_name=data['apellidos'],
                email=data['email'],
                phone=data.get('telefono', ''),
                faculty=data['facultad'],
                created_user=usuario,
            )

        return Response({
            'ok': True,
            'solicitud_id': solicitud.id,
            'message': 'Solicitud enviada. Un administrador la revisará pronto.',
        }, status=status.HTTP_201_CREATED)
