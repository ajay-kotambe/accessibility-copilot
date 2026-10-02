import asyncio
import time
from pathlib import Path
from django.utils import timezone
from playwright.async_api import async_playwright

from ..models import Scan, Page, Issue
from .url_security import normalize_url, is_private_host
from .axe_scanner import run_axe
from .custom_rules import run_custom_rules
from .scoring import calculate_score


AXE_PATH = Path(__file__).parent / 'axe.min.js'


def map_severity(impact):
    if not impact:
        return Issue.MODERATE
    impact = impact.upper()
    if impact == 'CRITICAL':
        return Issue.CRITICAL
    if impact == 'SERIOUS':
        return Issue.SERIOUS
    if impact == 'MODERATE':
        return Issue.MODERATE
    if impact == 'MINOR':
        return Issue.MINOR
    return Issue.MODERATE


def categorize(rule_id, tags=None):
    tags = tags or []
    rule_id = rule_id or ''
    tset = set(str(x).upper() for x in tags)
    if any(k in tset for k in ['COLOR-CONTRAST', 'COLOR']):
        return 'Color'
    if any(k in tset for k in ['IMAGE', 'ALT', 'IMAGES']):
        return 'Images'
    if any(k in tset for k in ['FORM', 'INPUT', 'LABEL']):
        return 'Forms'
    if any(k in tset for k in ['KEYBOARD', 'FOCUS']):
        return 'Keyboard'
    if any(k in tset for k in ['ARIA']):
        return 'ARIA'
    if any(k in tset for k in ['HEADING', 'HEADINGS', 'STRUCTURE']):
        return 'Structure'
    if any(k in tset for k in ['LANDMARK', 'NAVIGATION']):
        return 'Navigation'
    if any(k in tset for k in ['LINK', 'BUTTON']):
        return 'Navigation'
    return 'Content'


def wcag_category(tags=None):
    tags = tags or []
    tset = set(str(x).upper() for x in tags)
    if any('WCAG2AA' in x or 'WCAG2A' in x for x in tset):
        pass
    if any(k in tset for k in ['PERCEIVABLE']):
        return Issue.PERCEIVABLE
    if any(k in tset for k in ['OPERABLE']):
        return Issue.OPERABLE
    if any(k in tset for k in ['UNDERSTANDABLE']):
        return Issue.UNDERSTANDABLE
    if any(k in tset for k in ['ROBUST']):
        return Issue.ROBUST
    return ''


def run_scan(scan_id):
    asyncio.run(_run_scan(scan_id))


async def _run_scan(scan_id):
    scan = Scan.objects.get(id=scan_id)
    try:
        scan.status = Scan.CONNECTING
        scan.save()
        url = normalize_url(scan.url)
        parsed = __import__('urllib.parse').parse.urlparse(url)
        if is_private_host(parsed.netloc):
            raise ValueError('Private or unsafe URLs are not allowed')
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=[
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
            ])
            context = await browser.new_context()
            page = await context.new_page()
            scan.status = Scan.LOADING
            scan.save()
            try:
                await page.goto(url, timeout=30000, wait_until='networkidle')
            except Exception:
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            title = await page.title()
            scan_page = Page.objects.create(scan=scan, url=url, title=title or '')
            scan.status = Scan.SCANNING
            scan.save()
            if AXE_PATH.exists():
                await page.add_script_tag(path=str(AXE_PATH))
            else:
                await page.add_script_tag(url='https://unpkg.com/axe-core@4.10.0/axe.min.js')
            axe_result = await run_axe(page)
            issues = []
            if axe_result and not axe_result.get('error'):
                for v in axe_result.get('violations', []):
                    for n in v.get('nodes', []):
                        issues.append(Issue(
                            scan=scan,
                            page=scan_page,
                            rule_id=v.get('id'),
                            severity=map_severity(v.get('impact') or n.get('impact')),
                            category=categorize(v.get('id'), v.get('tags')),
                            description=v.get('description') or '',
                            selector='; '.join(n.get('target')) if n.get('target') else '',
                            html_snippet=n.get('html') or '',
                            help_url=v.get('helpUrl') or '',
                            impact=v.get('impact') or n.get('impact') or '',
                        ))
            custom = run_custom_rules(page)
            for c in custom:
                issues.append(Issue(scan=scan, page=scan_page, **c))
            scan.status = Scan.PROCESSING
            scan.save()
            Issue.objects.bulk_create(issues)
            score = calculate_score(issues)
            scan.score = score
            scan.status = Scan.COMPLETED
            scan.completed_at = timezone.now()
            scan.save()
            await browser.close()
    except Exception as e:
        scan.status = Scan.FAILED
        scan.error_message = str(e)
        scan.completed_at = timezone.now()
        scan.save()
        raise
