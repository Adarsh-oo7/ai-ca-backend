"""
Accounts App - URL Configuration
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', views.CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('google/', views.GoogleLoginView.as_view(), name='google_login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('onboarding/', views.OnboardingView.as_view(), name='onboarding'),
    path('preferences/', views.PreferenceView.as_view(), name='preferences'),
    path('activity/', views.ActivityLogListView.as_view(), name='activity_logs'),
]
