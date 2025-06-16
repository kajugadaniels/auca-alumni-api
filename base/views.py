from base.models import *
from base.pagination import *
from base.serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend

class StudentListView(generics.ListAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    pagination_class = CustomPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]

    # Fields allowed for searching and ordering
    search_fields = ['first_name', 'last_name', 'id_number']
    ordering_fields = ['id', 'first_name', 'last_name', 'id_number', 'created_at']
    ordering = ['id']