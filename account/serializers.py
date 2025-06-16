from base.models import *
from account.models import *
from rest_framework import serializers

class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'student_id']
        extra_kwargs = {'password': {'write_only': True}}

    def validate_student_id(self, value):
        if not Student.objects.filter(id=value).exists():
            raise serializers.ValidationError("Student ID does not exist.")
        return value

    def create(self, validated_data):
        return User.objects.create(**validated_data)
