from account.models import *
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import AccessToken

class VerifyTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"message": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = AccessToken(token)
            user_email = access_token.get("user_email")

            if not user_email:
                return Response({"message": "Invalid token payload."}, status=status.HTTP_401_UNAUTHORIZED)

            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            return Response({
                "message": "Token is valid.",
                "user": {
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_number": user.phone_number,
                    "student_id": user.student_id
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": "Invalid or expired token.", "error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
