import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the single student account if it does not exist'

    def handle(self, *args, **options):
        email = config('STUDENT_EMAIL', default=None)
        password = config('STUDENT_PASSWORD', default=None)

        if not email or not password:
            self.stdout.write(self.style.WARNING("STUDENT_EMAIL or STUDENT_PASSWORD is not set in environment. Skipping student seeding."))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f"Student user account '{email}' already exists."))
            return

        self.stdout.write(f"Creating student user account '{email}'...")
        user = User.objects.create_user(
            email=email,
            password=password,
            username=email.split('@')[0],
            is_student=True,
            is_staff=True,
            is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS(f"Successfully created student user account '{email}'. Profile & Preferences signals triggered!"))
