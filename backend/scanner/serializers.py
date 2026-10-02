from rest_framework import serializers
from .models import Scan, Page, Issue, AIAnalysis


class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = ['explanation', 'why_it_matters', 'suggested_fix', 'corrected_code', 'developer_tip']


class IssueSerializer(serializers.ModelSerializer):
    ai_analysis = AIAnalysisSerializer(read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'rule_id', 'severity', 'category', 'description', 'selector', 'html_snippet',
            'help_url', 'impact', 'ai_analysis'
        ]


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'url', 'title']


class ScanSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)
    issues = IssueSerializer(many=True, read_only=True)

    class Meta:
        model = Scan
        fields = [
            'id', 'url', 'status', 'score', 'started_at', 'completed_at', 'error_message', 'pages', 'issues'
        ]
        read_only_fields = ['status', 'score', 'started_at', 'completed_at', 'error_message']
