from base.models import *
from account.models import *
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth.hashers import make_password

class LoginUserSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # email or phone_number
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data.get('identifier')
        password = data.get('password')

        try:
            user = User.objects.get(models.Q(email=identifier) | models.Q(phone_number=identifier))
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with provided email or phone number.")

        if not check_password(password, user.password):
            raise serializers.ValidationError("Invalid password.")

        data['user'] = user
        return data

class RegisterUserSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'phone_number', 'student_id']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_student_id(self, value):
        if not Student.objects.filter(id=value).exists():
            raise serializers.ValidationError("Provided student_id does not exist.")
        return value

    def create(self, validated_data):
        student_id = validated_data.get('student_id')
        student = Student.objects.get(id=student_id)

        user = User.objects.create(
            email=validated_data['email'],
            password=make_password(validated_data['password']),
            phone_number=validated_data.get('phone_number'),
            student_id=student_id,
            first_name=student.first_name,
            last_name=student.last_name,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            is_staff=False,
            type="user"
        )
        return user
