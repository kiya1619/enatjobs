from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from functools import wraps

def role_required(*allowed_roles):
    """
    Allows access if the logged-in user has one of the allowed roles.
    Example:
        @role_required('admin', 'employer')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            # Check roles
            if ('admin' in allowed_roles and user.is_superuser) \
               or ('employer' in allowed_roles and user.is_employer) \
               or ('job_seeker' in allowed_roles and user.is_job_seeker):
                return view_func(request, *args, **kwargs)
            return redirect('job_seeker_dashboard')  # redirect unauthorized
        return _wrapped_view
    return decorator
