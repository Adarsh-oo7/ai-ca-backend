import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Notification
from apps.accounts.models import StudentPreference

logger = logging.getLogger('apps.notifications')

class NotificationSender:
    @staticmethod
    def send(user, title, message, notification_type='system', priority='medium', action_url='', action_label=''):
        """
        Creates an in-app Notification and sends an email if user preferences allow.
        """
        # 1. Create In-App Notification
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            action_url=action_url,
            action_label=action_label
        )

        # 2. Check student email preferences
        pref, _ = StudentPreference.objects.get_or_create(user=user)
        if pref.notification_email and settings.EMAIL_HOST_USER:
            try:
                subject = f"[Study Commander] {title}"
                email_body = f"""
                Hello!
                
                {message}
                
                To view this in your dashboard, click here: {settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else 'http://localhost:3000'}{action_url}
                
                Stay disciplined,
                Your CA Foundation AI Mentor
                """
                
                # Send email asynchronously or synchronously
                send_mail(
                    subject=subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
                
                notification.is_email_sent = True
                notification.email_sent_at = timezone.now()
                notification.save()
                
                logger.info(f"Successfully sent email notification to {user.email}")
            except Exception as e:
                logger.error(f"Error sending email to {user.email}: {e}")
                
        return notification
