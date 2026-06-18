"""
Study Commander AI - Production Settings
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

# Proxy SSL Header for Django to detect HTTPS behind reverse proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# JWT cookies must be secure in production and allow cross-site requests
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = True  # noqa: F405
SIMPLE_JWT['AUTH_COOKIE_SAMESITE'] = config('JWT_COOKIE_SAMESITE', default='None')  # noqa: F405

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging - less verbose in production
LOGGING['loggers']['apps']['level'] = 'WARNING'  # noqa: F405

# Cache timeout
CACHES['default']['TIMEOUT'] = 300  # noqa: F405
