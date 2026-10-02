from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from scanner.models import Issue, AIAnalysis
from .services import AIService


class AnalyzeIssueView(APIView):
    def post(self, request, id):
        issue = get_object_or_404(Issue, id=id)
        service = AIService()
        result = service.analyze_issue(issue)
        ai_analysis, _ = AIAnalysis.objects.update_or_create(
            issue=issue,
            defaults={
                'explanation': result.get('explanation', ''),
                'why_it_matters': result.get('why_it_matters', ''),
                'suggested_fix': result.get('suggested_fix', ''),
                'corrected_code': result.get('corrected_code', ''),
                'developer_tip': result.get('developer_tip', ''),
            }
        )
        return Response({
            'explanation': ai_analysis.explanation,
            'why_it_matters': ai_analysis.why_it_matters,
            'suggested_fix': ai_analysis.suggested_fix,
            'corrected_code': ai_analysis.corrected_code,
            'developer_tip': ai_analysis.developer_tip,
        })


class GenerateFixView(APIView):
    def post(self, request, id):
        issue = get_object_or_404(Issue, id=id)
        service = AIService()
        result = service.generate_fix(issue)
        ai_analysis, _ = AIAnalysis.objects.update_or_create(
            issue=issue,
            defaults={
                'explanation': result.get('explanation', ''),
                'why_it_matters': result.get('why_it_matters', ''),
                'suggested_fix': result.get('suggested_fix', ''),
                'corrected_code': result.get('corrected_code', ''),
                'developer_tip': result.get('developer_tip', ''),
            }
        )
        return Response({
            'explanation': ai_analysis.explanation,
            'why_it_matters': ai_analysis.why_it_matters,
            'suggested_fix': ai_analysis.suggested_fix,
            'corrected_code': ai_analysis.corrected_code,
            'developer_tip': ai_analysis.developer_tip,
        })
