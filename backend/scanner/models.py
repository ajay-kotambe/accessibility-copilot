from django.db import models


class Scan(models.Model):
    QUEUED = 'QUEUED'
    CONNECTING = 'CONNECTING'
    LOADING = 'LOADING'
    SCANNING = 'SCANNING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    STATUS_CHOICES = [
        (QUEUED, 'QUEUED'),
        (CONNECTING, 'CONNECTING'),
        (LOADING, 'LOADING'),
        (SCANNING, 'SCANNING'),
        (PROCESSING, 'PROCESSING'),
        (COMPLETED, 'COMPLETED'),
        (FAILED, 'FAILED'),
    ]

    url = models.URLField(max_length=2048)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=QUEUED)
    score = models.IntegerField(default=100, null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]


class Page(models.Model):
    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name='pages')
    url = models.URLField(max_length=2048)
    title = models.CharField(max_length=512, blank=True)

    class Meta:
        indexes = [models.Index(fields=['scan'])]


class Issue(models.Model):
    CRITICAL = 'CRITICAL'
    SERIOUS = 'SERIOUS'
    MODERATE = 'MODERATE'
    MINOR = 'MINOR'
    SEVERITY_CHOICES = [
        (CRITICAL, 'CRITICAL'),
        (SERIOUS, 'SERIOUS'),
        (MODERATE, 'MODERATE'),
        (MINOR, 'MINOR'),
    ]

    PERCEIVABLE = 'PERCEIVABLE'
    OPERABLE = 'OPERABLE'
    UNDERSTANDABLE = 'UNDERSTANDABLE'
    ROBUST = 'ROBUST'
    WCAG_CHOICES = [
        (PERCEIVABLE, 'PERCEIVABLE'),
        (OPERABLE, 'OPERABLE'),
        (UNDERSTANDABLE, 'UNDERSTANDABLE'),
        (ROBUST, 'ROBUST'),
    ]

    scan = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name='issues')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='issues', null=True, blank=True)
    rule_id = models.CharField(max_length=128)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES)
    category = models.CharField(max_length=32, blank=True)
    description = models.TextField()
    selector = models.TextField(blank=True)
    html_snippet = models.TextField(blank=True)
    help_url = models.URLField(max_length=2048, blank=True)
    impact = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['severity', 'rule_id']
        indexes = [
            models.Index(fields=['scan']),
            models.Index(fields=['severity']),
            models.Index(fields=['rule_id']),
        ]


class AIAnalysis(models.Model):
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE, related_name='ai_analysis')
    explanation = models.TextField()
    why_it_matters = models.TextField()
    suggested_fix = models.TextField()
    corrected_code = models.TextField()
    developer_tip = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
