from base.models import *
from rest_framework import serializers
from django.contrib.auth.models import User

class RegisterUserSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'student_id']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_student_id(self, value):
        if not Student.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid student ID: no matching student found.")
        return value

    def create(self, validated_data):
        student_id = validated_data.pop('student_id')
        user = User.objects.create_user(**validated_data)
        # optionally attach student_id somewhere if needed
        return user
