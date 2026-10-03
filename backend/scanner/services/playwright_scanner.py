import threading
from pathlib import Path
from django.db import connections
from django.utils import timezone
from playwright.sync_api import sync_playwright

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


def db(fn, *args, **kwargs):
    """Execute an ORM callable on a worker thread and return its result.

    Playwright's synchronous API drives an asyncio event loop inside the
    calling thread. Django's async-unsafe guard inspects for a running loop
    and rejects any ORM call made from that thread, so every write issued
    while the browser is open has to happen somewhere else. A fresh thread
    has no running loop, so the ORM call is legal there.
    """
    box = {}

    def runner():
        try:
            box['value'] = fn(*args, **kwargs)
        except Exception as exc:
            box['error'] = exc
        finally:
            connections.close_all()

    thread = threading.Thread(target=runner, name='scan-db')
    thread.start()
    thread.join()

    if 'error' in box:
        raise box['error']
    return box.get('value')


def _set_status(scan_id, status, **fields):
    """Persist a pipeline status transition from inside the browser block."""

    def apply():
        record = Scan.objects.get(id=scan_id)
        record.status = status
        for key, value in fields.items():
            setattr(record, key, value)
        record.save()

    db(apply)


def _inject_axe(context):
    """Load axe-core into every frame before navigation.

    page.add_script_tag() inserts an inline <script> element, which a site's
    Content-Security-Policy refuses whenever script-src omits 'unsafe-inline'
    (most large sites). context.add_init_script() goes through CDP's
    Page.addScriptToEvaluateOnNewDocument instead, so it is not subject to
    the page CSP and axe survives strict policies. axe-core only defines
    window.axe at this point; the actual run happens via page.evaluate() in
    run_axe(), which is likewise not CSP-gated.

    Returns False only if axe-core is not available locally, so the scan can
    still complete with the custom rules instead of failing outright.
    """
    if not AXE_PATH.exists():
        return False
    context.add_init_script(path=str(AXE_PATH))
    return True


def _short_error(exc, limit=300):
    """Keep browser/CSP noise out of error_message.

    CSP violations arrive as multi-kilobyte policy strings that are useless
    to a user and wreck the history layout.
    """
    text = ' '.join(str(exc).split())
    if len(text) <= limit:
        return text
    return text[:limit] + '...'


def run_scan(scan_id):
    """Execute the scan pipeline.

    Status transitions and issue persistence stay real: the POST handler
    blocks until the scan settles, so the client receives a terminal record.
    """
    scan = Scan.objects.get(id=scan_id)
    try:
        scan.status = Scan.CONNECTING
        scan.save()
        url = normalize_url(scan.url)
        parsed = __import__('urllib.parse').parse.urlparse(url)
        if is_private_host(parsed.netloc):
            raise ValueError('Private or unsafe URLs are not allowed')

        title = ''
        axe_result = {}
        custom = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
            ])
            context = browser.new_context()
            axe_loaded = _inject_axe(context)
            page = context.new_page()

            _set_status(scan_id, Scan.LOADING)
            try:
                page.goto(url, timeout=30000, wait_until='networkidle')
            except Exception:
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
            title = page.title() or ''

            _set_status(scan_id, Scan.SCANNING)
            # axe is already present via add_init_script; calling axe.run()
            # through page.evaluate() bypasses the page CSP.
            if axe_loaded:
                axe_result = run_axe(page) or {}
            else:
                axe_result = {'error': 'axe-core unavailable'}
            custom = run_custom_rules(page) or []
            custom = run_custom_rules(page) or []
            browser.close()

        _set_status(scan_id, Scan.PROCESSING)

        # Persist findings outside the browser block, where the ORM is legal
        # on the calling thread again.
        scan.refresh_from_db()
        scan_page = Page.objects.create(scan=scan, url=url, title=title)
        issues = []
        if not axe_result.get('error'):
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
        for c in custom:
            issues.append(Issue(scan=scan, page=scan_page, **c))

        Issue.objects.bulk_create(issues)
        score = calculate_score(issues)
        scan.score = score
        scan.status = Scan.COMPLETED
        scan.completed_at = timezone.now()
        scan.save()
    except Exception as e:
        Scan.objects.filter(id=scan_id).update(
            status=Scan.FAILED,
            error_message=_short_error(e),
            completed_at=timezone.now(),
        )
        raise
