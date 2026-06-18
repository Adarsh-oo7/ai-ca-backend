"""
Accounts App - Serializers
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, StudentProfile, StudentPreference, ActivityLog


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled.')
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_student']
        read_only_fields = ['id', 'email', 'is_student']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'preferred_name', 'exam_attempt', 'exam_date',
            'daily_study_hours', 'preferred_language', 'preferred_study_time',
            'strong_subjects', 'weak_subjects', 'onboarding_completed',
            'avatar_url', 'days_until_exam', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'days_until_exam', 'created_at', 'updated_at']


class OnboardingSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = StudentProfile
        fields = [
            'preferred_name', 'exam_attempt', 'exam_date',
            'daily_study_hours', 'preferred_language', 'preferred_study_time',
            'strong_subjects', 'weak_subjects', 'first_name', 'last_name',
        ]

    def update(self, instance, validated_data):
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)

        if first_name:
            instance.user.first_name = first_name
        if last_name:
            instance.user.last_name = last_name
        instance.user.save()

        instance.onboarding_completed = True
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class StudentPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentPreference
        fields = [
            'theme', 'voice_type', 'voice_enabled',
            'notification_email', 'notification_inapp',
            'notification_study_reminder', 'notification_revision_reminder',
            'notification_goal_reminder', 'notification_mock_reminder',
            'notification_missed_session',
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'details', 'device', 'timestamp']
        read_only_fields = ['id', 'timestamp']
