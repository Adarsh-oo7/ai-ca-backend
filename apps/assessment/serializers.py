from rest_framework import serializers
from .models import MockTest, MockQuestion, MockResult, MCQAttempt

class MockQuestionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = MockQuestion
        fields = [
            'id', 'test', 'question_text', 'question_image', 'options',
            'correct_answer', 'explanation', 'marks', 'difficulty',
            'subject', 'subject_name', 'chapter', 'chapter_name', 'topic', 'topic_name', 'order'
        ]
        # Hide correct answer and explanation during live test taking
        extra_kwargs = {
            'correct_answer': {'write_only': True},
            'explanation': {'write_only': True}
        }

class MockQuestionDetailSerializer(serializers.ModelSerializer):
    """Includes correct answer and explanation for review mode."""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = MockQuestion
        fields = '__all__'

class MockTestSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    test_type_display = serializers.CharField(source='get_test_type_display', read_only=True)

    class Meta:
        model = MockTest
        fields = [
            'id', 'title', 'description', 'test_type', 'test_type_display',
            'subject', 'subject_name', 'chapter', 'chapter_name', 'duration_minutes',
            'total_marks', 'total_questions', 'passing_marks', 'negative_marking',
            'negative_mark_value', 'is_ai_generated', 'is_published', 'difficulty_level',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_ai_generated', 'created_at']

class MockTestDetailSerializer(serializers.ModelSerializer):
    questions = MockQuestionSerializer(many=True, read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = MockTest
        fields = [
            'id', 'title', 'description', 'test_type', 'subject', 'subject_name',
            'chapter', 'chapter_name', 'duration_minutes', 'total_marks', 'total_questions',
            'passing_marks', 'negative_marking', 'negative_mark_value', 'is_ai_generated',
            'is_published', 'difficulty_level', 'questions', 'created_at'
        ]

class MCQAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MCQAttempt
        fields = '__all__'
        read_only_fields = ['id', 'is_correct', 'explanation', 'created_at']

class MockResultSerializer(serializers.ModelSerializer):
    test_title = serializers.CharField(source='test.title', read_only=True)
    test_type = serializers.CharField(source='test.test_type', read_only=True)

    class Meta:
        model = MockResult
        fields = [
            'id', 'test', 'test_title', 'test_type', 'score', 'total_marks',
            'correct_count', 'incorrect_count', 'unanswered_count',
            'accuracy_percentage', 'time_taken_minutes', 'analysis_json',
            'weak_areas', 'strong_areas', 'improvement_plan', 'ai_feedback',
            'readiness_impact', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'completed_at']
