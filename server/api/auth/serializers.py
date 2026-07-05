from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from core.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Devuelve info del usuario junto con los tokens."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = getattr(user, 'role', '')
        token['is_staff'] = user.is_staff
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'rol': getattr(user, 'role', ''),
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        }
        return data


class UsuarioMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'faculty', 'phone', 'is_staff', 'is_superuser',
        ]
        read_only_fields = fields
