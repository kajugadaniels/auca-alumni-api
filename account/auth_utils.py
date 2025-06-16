from django.contrib.auth import login
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def perform_session_login(request, user):
    # Prevent double login on anonymous model fallback
    if not isinstance(user, AnonymousUser):
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
