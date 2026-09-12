from django.conf import settings
from accounts.models import Notification

def site_context(request):
    notifications = []
    if request.user.is_authenticated:
        notifications = request.user.notifications.filter(is_read=False)[:5]

    return {
        'SITE_NAME': 'Co-opSeva',
        'AVAILABLE_LANGUAGES': settings.LANGUAGES,
        'CURRENT_LANGUAGE': getattr(request, 'LANGUAGE_CODE', 'en'),
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'unread_notifications': notifications,
    }
