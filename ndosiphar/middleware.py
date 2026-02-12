from django.conf import settings


class LocalhostCsrfTrustedMiddleware:
    """
    En mode DEBUG, autorise automatiquement toutes les origines localhost/127.0.0.1
    pour éviter les erreurs CSRF avec les proxys de développement.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            origin = request.META.get('HTTP_ORIGIN', '')
            if '127.0.0.1' in origin or 'localhost' in origin:
                # Ajouter dynamiquement l'origine aux origines de confiance
                if origin not in settings.CSRF_TRUSTED_ORIGINS:
                    settings.CSRF_TRUSTED_ORIGINS.append(origin)
        return self.get_response(request)
