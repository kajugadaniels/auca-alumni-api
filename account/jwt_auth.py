from account.models import *
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id = validated_token.get("user_id") or validated_token.get("user_email")
        if not user_id:
            raise InvalidToken("Token contained no identifiable user field.")
        
        try:
            return User.objects.get(email=user_id)
        except User.DoesNotExist:
            raise InvalidToken("User not found.")
