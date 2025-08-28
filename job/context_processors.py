from job.models import Notification

def notifications(request):
    if request.user.is_authenticated:
        # Get all notifications for the user, ordered by newest first
        all_notifications = request.user.notifications_received.order_by('-created_at')
        return {
            'notifications': all_notifications
        }
    return {}

def notification_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'notifications_unread_count': count}
    return {'notifications_unread_count': 0}