from account.models import *
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

class UserJWTAuthentication(JWTAuthentication):
    """
    Authenticates a JWT against the User model, using email from `user_email` claim.
    """
    user_id_claim = 'user_email'  # must match SIMPLE_JWT['USER_ID_CLAIM']

    def get_user(self, validated_token):
        user_email = validated_token.get(self.user_id_claim)
        if user_email is None:
            raise AuthenticationFailed('Token missing user email.', code='token_no_user_email')

        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found.', code='user_not_found')

        if not user.is_active:
            raise AuthenticationFailed('User is inactive.', code='user_inactive')

        return user
