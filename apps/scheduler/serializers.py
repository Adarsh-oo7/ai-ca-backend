from rest_framework import serializers
from .models import StudyTask, DailySchedule, WeeklySchedule, MonthlySchedule, ScheduleTemplate, Attendance

class StudyTaskSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)

    class Meta:
        model = StudyTask
        fields = [
            'id', 'title', 'description', 'task_type', 'task_type_display',
            'subject', 'subject_name', 'chapter', 'chapter_name', 'topic', 'topic_name',
            'scheduled_date', 'scheduled_time', 'duration_minutes', 'order',
            'status', 'priority', 'is_completed', 'completed_at', 'actual_duration',
            'is_ai_generated', 'ai_reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_ai_generated', 'ai_reason', 'created_at', 'updated_at']

class DailyScheduleSerializer(serializers.ModelSerializer):
    tasks = StudyTaskSerializer(many=True, read_only=True)

    class Meta:
        model = DailySchedule
        fields = [
            'id', 'date', 'tasks', 'hours_planned', 'hours_completed',
            'notes', 'is_holiday', 'ai_summary', 'created_at', 'updated_at'
        ]

class WeeklyScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklySchedule
        fields = '__all__'

class MonthlyScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlySchedule
        fields = '__all__'

class ScheduleTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleTemplate
        fields = '__all__'

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
