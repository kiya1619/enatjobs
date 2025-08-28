from django.db import models
from django.contrib.auth.models import  AbstractUser
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

# Create your models here.


class User(AbstractUser):
    is_employer = models.BooleanField(default=False)
    is_job_seeker = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='job_user_groups',  # Add this
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='job_user_permissions',  # Add this
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    @property
    def display_name(self):
        if hasattr(self, "seekerprofile"):
            return f"{self.seekerprofile.first_name.title()} {self.seekerprofile.last_name.title()}"
        elif hasattr(self, "employerprofile"):
            return self.employerprofile.comapany_name
        return self.username  #
class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    comapany_name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)
    About_company = models.TextField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)

class JobCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
class Job(models.Model):
    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True)
    required_skills = models.ManyToManyField("Skill", blank=True)

    location = models.CharField(max_length=255)
    job_type = models.CharField(max_length=50, choices=[('full-time','Full-time'),('part-time','Part-time'),('internship','Internship')])
    salary_range = models.CharField(max_length=50, blank=True)
    posted_on = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField()
    is_active = models.BooleanField(default=True)  # 👈 new field

    def is_still_active(self):
        return self.deadline >= timezone.now().date()

class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    applied_on = models.DateTimeField(auto_now_add=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=[
        ('applied','Applied'),
        ('reviewed','Reviewed'),
        ('rejected','Rejected'),
        ('accepted','Accepted')
    ], default='applied')
    cover_letter = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"

    @property
    def fallback_resume(self):   # 👈 renamed
        """Return resume from profile if application resume is missing."""
        if self.resume:
            return self.resume
        if hasattr(self.applicant, 'seekerprofile') and self.applicant.seekerprofile.resume:
            return self.applicant.seekerprofile.resume
        return None

class JobSeekerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    resume = models.FileField(upload_to='resumes/')
    skills = models.ManyToManyField("Skill", blank=True)
    experience = models.TextField(blank=True)
class SeekerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)  # 👈 free text (but controlled by form)

    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True)


class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    job_seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE)
    applied_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('applied','Applied'),('shortlisted','Shortlisted'),('interviewed','Interviewed'),('offered','Offered'),('rejected','Rejected')], default='applied')



class SavedJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    saved_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user.username} saved {self.job.title}"


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_received')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent')
    verb = models.CharField(max_length=255)  # e.g., "applied to"
    target = models.CharField(max_length=255, blank=True, null=True)  # e.g., job title
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.actor} {self.verb} {self.target}"


class Notification2(models.Model):
    NOTIFICATION_TYPES = [
        ('application', 'New Application'),
        ('job_expiry', 'Job Expired'),
        ('general', 'General Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications2')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(blank=True, null=True)  # Optional link to job or application
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
