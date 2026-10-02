from rest_framework import serializers
from scanner.models import AIAnalysis


class AIAnalysisRequestSerializer(serializers.Serializer):
    pass


class AIAnalysisResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = ['explanation', 'why_it_matters', 'suggested_fix', 'corrected_code', 'developer_tip']
