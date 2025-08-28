from django.utils import timezone
from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect

class AutoLogoutMiddleware:
    """
    Logs out users if they have been inactive for more than settings.AUTO_LOGOUT_DELAY seconds.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            current_time = timezone.now()
            last_activity = request.session.get('last_activity')

            if last_activity:
                try:
                    last_activity_time = timezone.datetime.fromisoformat(last_activity)
                    # Make last_activity_time timezone-aware if not
                    if timezone.is_naive(last_activity_time):
                        last_activity_time = timezone.make_aware(last_activity_time, timezone.get_current_timezone())
                except ValueError:
                    # If stored value is invalid, reset it
                    last_activity_time = current_time

                elapsed = (current_time - last_activity_time).total_seconds()
                if elapsed > getattr(settings, 'AUTO_LOGOUT_DELAY', 300):  # default 30 min
                    auth.logout(request)
                    return redirect('login')  # redirect after logout

            # Update last activity
            request.session['last_activity'] = current_time.isoformat()

        response = self.get_response(request)
        return response
