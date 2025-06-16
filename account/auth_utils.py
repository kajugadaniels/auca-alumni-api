import jwt
import datetime
from django.conf import settings

def get_tokens_for_user(user):
    from rest_framework_simplejwt.settings import api_settings

    now = datetime.datetime.utcnow()

    access_payload = {
        "token_type": "access",
        "exp": now + api_settings.ACCESS_TOKEN_LIFETIME,
        "iat": now,
        settings.SIMPLE_JWT["USER_ID_CLAIM"]: user.email,
    }

    refresh_payload = {
        "token_type": "refresh",
        "exp": now + api_settings.REFRESH_TOKEN_LIFETIME,
        "iat": now,
        settings.SIMPLE_JWT["USER_ID_CLAIM"]: user.email,
    }

    access_token = jwt.encode(access_payload, settings.SIMPLE_JWT["SIGNING_KEY"], algorithm=settings.SIMPLE_JWT["ALGORITHM"])
    refresh_token = jwt.encode(refresh_payload, settings.SIMPLE_JWT["SIGNING_KEY"], algorithm=settings.SIMPLE_JWT["ALGORITHM"])

    return {
        "access": access_token,
        "refresh": refresh_token
    }
