# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import JobApplication, Notification2  # use Notification2 instead

print("Jobs signals module loaded!")  # Optional: confirms signals.py is loaded


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