from django.apps import AppConfig


class JobConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'job'
    def ready(self):
        # Import signals here
        import job.signals
