"""
Google Calendar Integration Service
Handles OAuth2 flow, event creation, and bidirectional sync of study tasks.
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('apps.scheduler')


class GoogleCalendarService:
    """Service for Google Calendar OAuth2 and event management."""

    SCOPES = ['https://www.googleapis.com/auth/calendar.events']

    @staticmethod
    def get_auth_url(user):
        """Generate OAuth2 authorization URL for Google Calendar access."""
        try:
            from google_auth_oauthlib.flow import Flow

            client_id = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_ID', '')
            client_secret = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_SECRET', '')
            redirect_uri = getattr(settings, 'GOOGLE_CALENDAR_REDIRECT_URI', '')

            if not client_id or not client_secret:
                raise ValueError("Google Calendar credentials not configured")

            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=GoogleCalendarService.SCOPES,
                redirect_uri=redirect_uri,
            )

            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                state=str(user.id)
            )

            return auth_url, state

        except ImportError:
            logger.error("google-auth-oauthlib is not installed. Run: pip install google-auth-oauthlib google-api-python-client")
            raise ValueError("Google Calendar integration dependencies not installed")

    @staticmethod
    def handle_callback(user, auth_code):
        """Exchange authorization code for tokens and store them."""
        try:
            from google_auth_oauthlib.flow import Flow
            from .models import GoogleCalendarToken

            client_id = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_ID', '')
            client_secret = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_SECRET', '')
            redirect_uri = getattr(settings, 'GOOGLE_CALENDAR_REDIRECT_URI', '')

            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=GoogleCalendarService.SCOPES,
                redirect_uri=redirect_uri,
            )

            flow.fetch_token(code=auth_code)
            credentials = flow.credentials

            # Store tokens
            token_obj, created = GoogleCalendarToken.objects.update_or_create(
                user=user,
                defaults={
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token or '',
                    'token_expiry': credentials.expiry or (timezone.now() + timedelta(hours=1)),
                    'is_active': True,
                }
            )

            return token_obj

        except Exception as e:
            logger.error(f"Google Calendar callback failed for {user.email}: {e}")
            raise

    @staticmethod
    def _get_credentials(user):
        """Get valid Google credentials for a user, refreshing if needed."""
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from .models import GoogleCalendarToken

        try:
            token_obj = GoogleCalendarToken.objects.get(user=user, is_active=True)
        except GoogleCalendarToken.DoesNotExist:
            raise ValueError("Google Calendar not connected")

        client_id = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_ID', '')
        client_secret = getattr(settings, 'GOOGLE_CALENDAR_CLIENT_SECRET', '')

        credentials = Credentials(
            token=token_obj.access_token,
            refresh_token=token_obj.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=GoogleCalendarService.SCOPES,
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            token_obj.access_token = credentials.token
            token_obj.token_expiry = credentials.expiry or (timezone.now() + timedelta(hours=1))
            token_obj.save(update_fields=['access_token', 'token_expiry'])

        return credentials, token_obj.calendar_id

    @staticmethod
    def sync_task_to_calendar(user, task):
        """Create or update a Google Calendar event from a StudyTask."""
        try:
            from googleapiclient.discovery import build

            credentials, calendar_id = GoogleCalendarService._get_credentials(user)
            service = build('calendar', 'v3', credentials=credentials)

            # Build event datetime
            task_date = task.scheduled_date
            if task.scheduled_time:
                start_dt = datetime.combine(task_date, task.scheduled_time)
            else:
                start_dt = datetime.combine(task_date, datetime.strptime("10:00", "%H:%M").time())

            end_dt = start_dt + timedelta(minutes=task.duration_minutes)

            # Color based on task type
            color_map = {
                'study': '9',        # Blueberry
                'revision': '2',     # Sage
                'mcq_practice': '5', # Banana
                'mock_test': '11',   # Tomato
                'doubt_solving': '7', # Peacock
                'notes': '3',       # Grape
            }

            event_body = {
                'summary': f"📚 {task.title}",
                'description': (
                    f"Task Type: {task.get_task_type_display()}\n"
                    f"Subject: {task.subject.name if task.subject else 'General'}\n"
                    f"Duration: {task.duration_minutes} mins\n"
                    f"Priority: {task.get_priority_display()}\n"
                    f"{task.description}\n\n"
                    f"{'🤖 AI Generated: ' + task.ai_reason if task.is_ai_generated else ''}"
                ),
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'colorId': color_map.get(task.task_type, '1'),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }

            if task.google_event_id:
                # Update existing event
                event = service.events().update(
                    calendarId=calendar_id,
                    eventId=task.google_event_id,
                    body=event_body
                ).execute()
            else:
                # Create new event
                event = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body
                ).execute()

            # Store the event ID on the task
            task.google_event_id = event['id']
            task.save(update_fields=['google_event_id'])

            return event

        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to Google Calendar: {e}")
            raise

    @staticmethod
    def sync_all_tasks(user, target_date):
        """Sync all tasks for a specific date to Google Calendar."""
        from .models import StudyTask

        tasks = StudyTask.objects.filter(
            user=user,
            scheduled_date=target_date
        )

        synced = 0
        errors = 0
        for task in tasks:
            try:
                GoogleCalendarService.sync_task_to_calendar(user, task)
                synced += 1
            except Exception as e:
                errors += 1
                logger.error(f"Sync error for task {task.id}: {e}")

        return {'synced': synced, 'errors': errors}

    @staticmethod
    def delete_calendar_event(user, event_id):
        """Remove an event from Google Calendar."""
        try:
            from googleapiclient.discovery import build

            credentials, calendar_id = GoogleCalendarService._get_credentials(user)
            service = build('calendar', 'v3', credentials=credentials)

            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            return True
        except Exception as e:
            logger.error(f"Failed to delete calendar event {event_id}: {e}")
            return False

    @staticmethod
    def disconnect(user):
        """Revoke Google Calendar access and delete stored tokens."""
        from .models import GoogleCalendarToken

        try:
            token_obj = GoogleCalendarToken.objects.get(user=user)
            
            # Try to revoke the token
            try:
                import requests as http_requests
                http_requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': token_obj.access_token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            except Exception:
                pass  # Revocation is best-effort

            token_obj.delete()
            return True
        except GoogleCalendarToken.DoesNotExist:
            return False
