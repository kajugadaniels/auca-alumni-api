from account.auth_utils import *
from account.audit_logs import *
from rest_framework import status
from account.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response

class LoginUserView(APIView):
    def post(self, request):
        serializer = LoginUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Log event
            log_login_event(user, request)

            # Perform session login
            perform_session_login(request, user)

            # Issue JWT tokens
            tokens = get_tokens_for_user(user)

            return Response({
                "message": "Login successful.",
                "tokens": tokens,
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "student_id": user.student_id
                }
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Login failed.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class RegisterUserView(APIView):
    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User registered successfully.",
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "student_id": user.student_id
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            "message": "Registration failed.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)