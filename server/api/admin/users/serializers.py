from rest_framework import serializers

from core.models import User


class UsuarioListSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_role_display', read_only=True)
    facultad_display = serializers.CharField(source='get_faculty_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'rol_display', 'faculty', 'facultad_display',
            'phone', 'is_staff', 'is_superuser', 'is_active',
            'date_joined', 'last_login',
        ]
        read_only_fields = ('date_joined', 'last_login')


class UsuarioWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=4)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'role', 'faculty', 'phone', 'is_staff', 'is_active', 'password',
        ]

    def create(self, validated_data):
        pwd = validated_data.pop('password', None) or '123'
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user

    def update(self, instance, validated_data):
        pwd = validated_data.pop('password', None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if pwd:
            instance.set_password(pwd)
        instance.save()
        return instance


class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=4, write_only=True)
