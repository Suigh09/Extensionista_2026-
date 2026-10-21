from django.contrib import admin

from .models import ClassOffering, Course, ProfessorProfile, StudentProfile, Subject

admin.site.register([Course, Subject, ClassOffering, StudentProfile, ProfessorProfile])
