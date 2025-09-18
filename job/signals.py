# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import JobApplication, Notification2  # use Notification2 instead
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import LoginActivity
from django.contrib.auth.signals import user_login_failed
from .models import FailedLoginAttempt
from django.utils import timezone



@receiver(post_save, sender=JobApplication)
def create_application_notification(sender, instance, created, **kwargs):
    if created:
        employer_user = instance.job.employer.user
        applicant_name = instance.applicant.get_full_name() or instance.applicant.username

        Notification2.objects.create(
            user=employer_user,
            notification_type='application',
            title='New Job Application',
            message=f'{applicant_name} applied for {instance.job.title}.',
            link=f'/employer/job/{instance.job.id}/applications/'
        )
        print(f"Notification created for employer: {employer_user.username}")

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    LoginActivity.objects.create(user=user, ip_address=ip, user_agent=user_agent)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

