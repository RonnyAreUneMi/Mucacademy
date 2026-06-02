from django.contrib.auth.backends import ModelBackend
from core.models import User


class EmailBackend(ModelBackend):
    """Custom authentication backend that allows login with email or username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try email first
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            try:
                # Fall back to username
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
        
        if user.check_password(password):
            return user
        return None
