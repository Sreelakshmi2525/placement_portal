# jobs/admin.py
from django.contrib import admin
from .models import Job, Department

admin.site.register(Job)
admin.site.register(Department)