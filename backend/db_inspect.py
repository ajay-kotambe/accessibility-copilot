"""Print a readable summary of the SQLite database. Run with:
    venv\Scripts\python.exe db_inspect.py
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from scanner.models import Scan, Page, Issue, AIAnalysis

print('=' * 78)
print('DATABASE:', connection.settings_dict['NAME'])
print('=' * 78)

with connection.cursor() as c:
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    print('tables:', ', '.join(r[0] for r in c.fetchall()))
print()

print(f'Scan: {Scan.objects.count()}   Page: {Page.objects.count()}   '
      f'Issue: {Issue.objects.count()}   AIAnalysis: {AIAnalysis.objects.count()}')
print()

print('-' * 78)
print('SCANS')
print('-' * 78)
print(f"{'id':>4}  {'status':<11} {'score':>5}  {'issues':>6}  {'url'}")
for s in Scan.objects.order_by('-id'):
    print(f'{s.id:>4}  {s.status:<11} {str(s.score):>5}  {s.issues.count():>6}  {s.url[:52]}')
    if s.error_message:
        print(f'        error: {s.error_message[:70]}')
print()

print('-' * 78)
print('ISSUES BY SEVERITY')
print('-' * 78)
for sev in ('CRITICAL', 'SERIOUS', 'MODERATE', 'MINOR'):
    ids = Issue.objects.filter(severity=sev).values_list('id', flat=True)
    print(f'  {sev:<9} {len(ids)}')
print()

print('-' * 78)
print('TOP 10 RULES TRIGGERED')
print('-' * 78)
for issue in Issue.objects.values('rule_id').annotate(n=__import__('django').db.models.Count('id')).order_by('-n')[:10]:
    print(f'  {issue["n"]:>4}  {issue["rule_id"]}')
print()

print('-' * 78)
print('SAMPLE ISSUE + AI ANALYSIS')
print('-' * 78)
issue = Issue.objects.filter(ai_analysis__isnull=False).order_by('-id').first()
if issue:
    print('rule_id      :', issue.rule_id)
    print('severity     :', issue.severity)
    print('selector     :', issue.selector[:80])
    print('html_snippet :', issue.html_snippet[:80])
    ai = issue.ai_analysis
    print('\nAI brief:')
    print('  why_it_matters  :', (ai.why_it_matters or '')[:100])
    print('  suggested_fix   :', (ai.suggested_fix or '')[:100])
    print('  corrected_code  :', (ai.corrected_code or '')[:100].replace('\n', ' '))
    print('  developer_tip   :', (ai.developer_tip or '')[:100])
else:
    print('none yet')