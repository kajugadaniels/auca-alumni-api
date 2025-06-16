from django.db import models

class Student(models.Model):
    id = models.BigAutoField(primary_key=True)
    id_number = models.IntegerField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(null=True)

    class Meta:
        db_table = 'students'
        managed = False  # Prevent Django from managing the table