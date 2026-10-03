import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scanner.models import AIAnalysis, Issue

from .serializers import AIAnalysisResponseSerializer
from .services import AIService, AIServiceError

logger = logging.getLogger(__name__)

FIELDS = (
    'explanation',
    'why_it_matters',
    'suggested_fix',
    'corrected_code',
    'developer_tip',
)


def _run_and_store(issue, run):
    """Call Gemini, persist the brief, and return the API payload.

    A provider failure is logged with the precise reason and answered with a
    generic message, so neither the API key nor a stack trace reaches the
    browser.
    """
    try:
        result = run()
    except AIServiceError as exc:
        logger.warning('Gemini request failed for issue %s: %s', issue.pk, exc.reason)
        return Response({'detail': exc.user_message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    analysis, _ = AIAnalysis.objects.update_or_create(
        issue=issue,
        defaults={field: result.get(field, '') for field in FIELDS},
    )
    return Response(AIAnalysisResponseSerializer(analysis).data)


class AnalyzeIssueView(APIView):
    """Explain a real axe-core finding."""

    def post(self, request, id):
        issue = get_object_or_404(Issue, id=id)
        service = AIService()
        return _run_and_store(issue, lambda: service.analyze_issue(issue))


class GenerateFixView(APIView):
    """Produce a corrected snippet for a real axe-core finding."""

    def post(self, request, id):
        issue = get_object_or_404(Issue, id=id)
        service = AIService()
        return _run_and_store(issue, lambda: service.generate_fix(issue))