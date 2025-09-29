"""
Custom middleware for Carematix
"""

from django.utils.deprecation import MiddlewareMixin


class DisableCSRFMiddleware(MiddlewareMixin):
    """
    Middleware to disable CSRF protection for API endpoints
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        # Disable CSRF for API endpoints
        if request.path.startswith('/api/'):
            return None  # Skip CSRF processing
        return None
