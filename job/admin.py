from django.contrib import admin
from .models import User, EmployerProfile, JobCategory, Job, JobSeekerProfile, Application,Skill

admin.site.register(User)
admin.site.register(EmployerProfile)
admin.site.register(JobCategory)
admin.site.register(Job)
admin.site.register(JobSeekerProfile)
admin.site.register(Application)
admin.site.register(Skill)
