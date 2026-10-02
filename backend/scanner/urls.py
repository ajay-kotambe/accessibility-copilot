from django.urls import path
from . import views

urlpatterns = [
    path('scans/', views.ScanListCreateView.as_view(), name='scan-list-create'),
    path('scans/history/', views.ScanHistoryView.as_view(), name='scan-history'),
    path('scans/<int:id>/', views.ScanDetailView.as_view(), name='scan-detail'),
    path('scans/<int:id>/issues/', views.ScanIssuesView.as_view(), name='scan-issues'),
]
