from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Scan, Page, Issue
from .serializers import ScanSerializer, IssueSerializer
from .services.playwright_scanner import run_scan


class ScanListCreateView(APIView):
    def get(self, request):
        scans = Scan.objects.all()[:50]
        serializer = ScanSerializer(scans, many=True)
        return Response(serializer.data)

    def post(self, request):
        url = request.data.get('url')
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        scan = Scan.objects.create(url=url, status=Scan.QUEUED)
        try:
            run_scan(scan.id)
        except Exception as e:
            scan.status = Scan.FAILED
            scan.error_message = str(e)
            scan.completed_at = timezone.now()
            scan.save()
            return Response({'error': str(e), 'scan_id': scan.id}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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
