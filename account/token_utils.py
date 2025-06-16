import secrets
from datetime import datetime
from account.models import AuthToken

def get_or_create_token_for_user(user):
    try:
        token = AuthToken.objects.get(user_id=user.id)
    except AuthToken.DoesNotExist:
        token = AuthToken.objects.create(
            key=secrets.token_hex(20),
            user_id=user.id,
            created=datetime.now()
        )
    return token
