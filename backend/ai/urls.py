from django.urls import path
from . import views

urlpatterns = [
    path('issues/<int:id>/analyze/', views.AnalyzeIssueView.as_view(), name='analyze-issue'),
    path('issues/<int:id>/generate-fix/', views.GenerateFixView.as_view(), name='generate-fix'),
]
