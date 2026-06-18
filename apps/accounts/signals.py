"""
Accounts App - Signals
Auto-create StudentProfile and Preferences on user creation.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, StudentProfile, StudentPreference


@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """Create a StudentProfile and Preferences when a User is created."""
    if created and instance.is_student:
        StudentProfile.objects.create(user=instance)
        StudentPreference.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """Save the StudentProfile when the User is saved."""
    if instance.is_student:
        if hasattr(instance, 'student_profile'):
            instance.student_profile.save()
