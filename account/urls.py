from account.views import *
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

app_name = 'auth'

urlpatterns = [
    path('login/', LoginUserView.as_view(), name='login'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('verify-token/', VerifyUserTokenView.as_view(), name='verify-token'),
]  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)