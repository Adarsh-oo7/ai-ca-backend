"""
Accounts App - Views
"""
import random
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import login

from .models import User, StudentProfile, StudentPreference, ActivityLog
from .serializers import (
    LoginSerializer, UserSerializer, StudentProfileSerializer,
    OnboardingSerializer, StudentPreferenceSerializer, ActivityLogSerializer,
)


class LoginView(APIView):
    """Email/password login — returns JWT tokens (DISABLED)."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        return Response(
            {'detail': 'Password-based login is disabled. Please request an OTP to log in.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class SendOTPView(APIView):
    """Send OTP code to robodevika@gmail.com (or config'd student email)"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'detail': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_email = getattr(settings, 'STUDENT_EMAIL', 'robodevika@gmail.com').strip().lower()
        if email != allowed_email:
            return Response({'detail': f'Access denied. Only {allowed_email} is authorized.'}, status=status.HTTP_403_FORBIDDEN)

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store in cache for 5 minutes (300 seconds)
        cache.set(f"otp_{email}", otp, 300)

        # Send email
        try:
            send_mail(
                subject="[Study Commander] Your OTP Login Code",
                message=f"Hello,\n\nYour OTP login code is: {otp}\n\nThis code will expire in 5 minutes.\n\nYour CA Foundation AI Mentor",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            return Response({'detail': f'OTP sent successfully to {email}.'})
        except Exception as e:
            # Fallback for dev print
            print(f"Failed to send email to {email}: {e}. OTP generated: {otp}")
            # If in debug mode, return the OTP for testing convenience
            if settings.DEBUG:
                return Response({
                    'detail': f'Failed to send email: {str(e)}',
                    'otp_fallback': otp
                }, status=status.HTTP_200_OK)
            return Response({'detail': 'Failed to send OTP email. Please check server configuration.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    """Verify OTP and authenticate user"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        otp = request.data.get('otp', '').strip()
        device = request.data.get('device', 'web')

        if not email or not otp:
            return Response({'detail': 'Email and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

        allowed_email = getattr(settings, 'STUDENT_EMAIL', 'robodevika@gmail.com').strip().lower()
        if email != allowed_email:
            return Response({'detail': f'Access denied. Only {allowed_email} is authorized.'}, status=status.HTTP_403_FORBIDDEN)

        cached_otp = cache.get(f"otp_{email}")

        if not cached_otp or cached_otp != otp:
            return Response({'detail': 'Invalid or expired OTP. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        # Clear OTP from cache
        cache.delete(f"otp_{email}")

        # Retrieve or create user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'is_student': True,
                'is_staff': True,
                'is_superuser': True
            }
        )

        refresh = RefreshToken.for_user(user)
        
        # Log activity
        ActivityLog.objects.create(
            user=user,
            action='login',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            device=device,
        )

        response = Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'onboarding_completed': getattr(
                user, 'student_profile', None
            ) and user.student_profile.onboarding_completed or False,
        })

        # Set refresh token as httpOnly cookie
        jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
        cookie_samesite = jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax')
        cookie_secure = jwt_settings.get('AUTH_COOKIE_SECURE', request.is_secure())

        response.set_cookie(
            'refresh_token',
            str(refresh),
            httponly=True,
            samesite=cookie_samesite,
            secure=cookie_secure,
            max_age=90 * 24 * 60 * 60,  # 90 days
        )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class LogoutView(APIView):
    """Invalidate refresh token."""

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh') or request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            ActivityLog.objects.create(
                user=request.user,
                action='logout',
            )

            response = Response({'detail': 'Logged out successfully.'})
            
            from django.conf import settings
            jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
            cookie_samesite = jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax')
            cookie_secure = jwt_settings.get('AUTH_COOKIE_SECURE', request.is_secure())
            
            response.delete_cookie(
                'refresh_token',
                samesite=cookie_samesite,
                secure=cookie_secure
            )
            return response
        except Exception:
            return Response({'detail': 'Logged out.'}, status=status.HTTP_200_OK)


class CookieTokenRefreshView(TokenRefreshView):
    """
    Custom TokenRefreshView that reads the refresh token from cookies
    if it's not present in the request body, and sets the rotated refresh token
    as an httpOnly cookie in the response.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        raw_data = request.data.copy() if hasattr(request.data, 'copy') else {}
        
        if not raw_data.get('refresh'):
            cookie_refresh = request.COOKIES.get('refresh_token')
            if cookie_refresh:
                raw_data['refresh'] = cookie_refresh
        
        serializer = self.get_serializer(data=raw_data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'detail': 'Token is invalid or expired.'}, status=status.HTTP_401_UNAUTHORIZED)
            
        response_data = serializer.validated_data
        response = Response(response_data, status=status.HTTP_200_OK)
        
        new_refresh = response_data.get('refresh')
        if new_refresh:
            from django.conf import settings
            jwt_settings = getattr(settings, 'SIMPLE_JWT', {})
            cookie_samesite = jwt_settings.get('AUTH_COOKIE_SAMESITE', 'Lax')
            cookie_secure = jwt_settings.get('AUTH_COOKIE_SECURE', request.is_secure())
            
            response.set_cookie(
                'refresh_token',
                new_refresh,
                httponly=True,
                samesite=cookie_samesite,
                secure=cookie_secure,
                max_age=7 * 24 * 60 * 60,
            )
        return response


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update student profile."""
    serializer_class = StudentProfileSerializer

    def get_object(self):
        profile, _ = StudentProfile.objects.get_or_create(user=self.request.user)
        return profile


class OnboardingView(APIView):
    """Complete student onboarding."""

    def post(self, request):
        profile, _ = StudentProfile.objects.get_or_create(user=request.user)
        serializer = OnboardingSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            StudentProfileSerializer(profile).data,
            status=status.HTTP_200_OK,
        )


class PreferenceView(generics.RetrieveUpdateAPIView):
    """Get or update student preferences."""
    serializer_class = StudentPreferenceSerializer

    def get_object(self):
        prefs, _ = StudentPreference.objects.get_or_create(user=self.request.user)
        return prefs


class ActivityLogListView(generics.ListAPIView):
    """List recent activity logs."""
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(user=self.request.user)[:50]


class GoogleLoginView(APIView):
    """Handle Google OAuth login."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # Google token validation happens via allauth
        # This endpoint is a wrapper that returns JWT tokens
        from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
        from dj_rest_auth.registration.views import SocialLoginView

        # Delegate to dj-rest-auth's social login
        return SocialLoginView.as_view(adapter_class=GoogleOAuth2Adapter)(request._request)
