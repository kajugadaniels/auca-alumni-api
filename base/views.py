from base.models import *
from base.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response

class StudentListView(APIView):
    def get(self, request):
        students = Student.objects.all()
        serializer = StudentSerializer(students, many=True)
        return Response(serializer.data)
