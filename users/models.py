# users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('placement_officer', 'Placement Officer'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    
    def is_student(self):
        return self.user_type == 'student'
    
    def is_placement_officer(self):
        return self.user_type == 'placement_officer'

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=20)
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField()

    image = models.ImageField(
        upload_to='profile_images/', 
        default='profile_images/default.jpg',  # Set a default image
        blank=True, 
        null=True
    )
    resume = models.FileField(
        upload_to='resumes/', 
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc'])],
        blank=True, 
        null=True
    )
    def __str__(self):
        return f"{self.user.username} - {self.roll_number}"