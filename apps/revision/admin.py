from django.contrib import admin
from .models import RevisionTask

@admin.register(RevisionTask)
class RevisionTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'chapter', 'due_date', 'interval_days', 'easiness_factor', 'repetitions', 'status']
    list_filter = ['status', 'due_date', 'subject']
    search_fields = ['title']
