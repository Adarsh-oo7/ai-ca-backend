"""
Study Commander AI - Development Settings
"""
from .base import *  # noqa: F401, F403

DEBUG = True

INSTALLED_APPS += ['django_extensions', 'debug_toolbar']  # noqa: F405

MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405

INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Allow browsable API in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (  # noqa: F405
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

# Disable throttling in dev
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa: F405
    'anon': '1000/minute',
    'user': '5000/minute',
}

# Console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Logging
LOGGING['loggers']['apps']['level'] = 'DEBUG'  # noqa: F405
