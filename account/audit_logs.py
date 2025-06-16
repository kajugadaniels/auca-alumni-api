import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def log_login_event(user, request):
    ip = get_client_ip(request)
    logger.info(f"[LOGIN] {user.email} at {datetime.now().isoformat()} from IP {ip}")

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
