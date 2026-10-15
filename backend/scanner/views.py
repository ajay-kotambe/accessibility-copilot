import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Scan, Page, Issue
from .serializers import ScanSerializer, IssueSerializer
from .services.navigation_errors import user_message_for
from .services.playwright_scanner import run_scan

logger = logging.getLogger(__name__)


class ScanListCreateView(APIView):
    def get(self, request):
        scans = Scan.objects.all()[:50]
        serializer = ScanSerializer(scans, many=True)
        return Response(serializer.data)

    def post(self, request):
        url = request.data.get('url')
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            scan = Scan.objects.create(url=url, status=Scan.QUEUED)
        except Exception:
            # The queue write happens before Playwright is ever started, so a
            # database failure here (unapplied migrations, unreachable database)
            # would otherwise surface only as an opaque Django 500. Log the full
            # traceback server-side; the client gets a generic sentence.
            logger.exception('Failed to create scan record for url=%r', url)
            return Response(
                {'error': 'The scan could not be started. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            run_scan(scan.id)
        except Exception as e:
            # The raw error is logged by the scanner; only the friendly message
            # is persisted and returned. A failed scan gets no accessibility
            # score. The response keys are unchanged.
            message = user_message_for(e)
            scan.refresh_from_db()
            scan.status = Scan.FAILED
            scan.error_message = message
            scan.score = None
            scan.completed_at = scan.completed_at or timezone.now()
            scan.save()
            return Response({'error': message, 'scan_id': scan.id}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        scan.refresh_from_db()
        serializer = ScanSerializer(scan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScanDetailView(APIView):
    def get(self, request, id):
        scan = get_object_or_404(Scan, id=id)
        serializer = ScanSerializer(scan)
        return Response(serializer.data)


class ScanIssuesView(APIView):
    def get(self, request, id):
        scan = get_object_or_404(Scan, id=id)
        issues = scan.issues.all()
        serializer = IssueSerializer(issues, many=True)
        return Response(serializer.data)


class ScanHistoryView(APIView):
    def get(self, request):
        scans = Scan.objects.all()[:20]
        serializer = ScanSerializer(scans, many=True)
        return Response(serializer.data)
