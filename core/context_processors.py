from django.conf import settings


def site_context(request):
    return {
        'SITE_NAME': 'Co-opSeva',
        'AVAILABLE_LANGUAGES': settings.LANGUAGES,
        'CURRENT_LANGUAGE': getattr(request, 'LANGUAGE_CODE', 'en'),
    }
