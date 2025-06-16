from django.db import models

class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(unique=True)
    email_verified_at = models.DateTimeField(null=True)
    password = models.CharField(max_length=255)
    remember_token = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(null=True)
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    phone_number = models.CharField(max_length=255, null=True)
    is_staff = models.BooleanField(null=True)
    student_id = models.IntegerField()
    type = models.CharField(max_length=255, null=True)

    class Meta:
        db_table = 'users'
        managed = False
