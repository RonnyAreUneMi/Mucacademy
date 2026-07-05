from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import CustomTokenObtainPairSerializer, UsuarioMeSerializer


class LoginView(TokenObtainPairView):
    """POST email/username + password → access + refresh tokens + user info."""
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """GET: devuelve los datos del usuario autenticado."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UsuarioMeSerializer(request.user).data)
