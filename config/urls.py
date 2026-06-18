"""
Study Commander AI - URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API v1
    path('api/auth/', include('apps.accounts.urls')),
    path('api/memory/', include('apps.memory.urls')),
    path('api/knowledge/', include('apps.knowledge.urls')),
    path('api/curriculum/', include('apps.curriculum.urls')),
    path('api/ai/', include('apps.ai_engine.urls')),
    path('api/schedule/', include('apps.scheduler.urls')),
    path('api/assessment/', include('apps.assessment.urls')),
    path('api/revision/', include('apps.revision.urls')),
    path('api/analytics/', include('apps.analytics.urls')),
    path('api/accountability/', include('apps.accountability.urls')),
    path('api/notifications/', include('apps.notifications.urls')),

    # Allauth
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass

# Admin customization
admin.site.site_header = 'Study Commander AI'
admin.site.site_title = 'Study Commander AI Admin'
admin.site.index_title = 'Control Center'
