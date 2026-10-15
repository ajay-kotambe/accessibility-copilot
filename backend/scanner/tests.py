from pathlib import Path
from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from rest_framework.test import APIClient

from scanner.models import Scan
from scanner.services.navigation_errors import (
    MESSAGE_CONNECTION,
    MESSAGE_DNS,
    MESSAGE_GENERIC,
    MESSAGE_TIMEOUT,
    ScanNavigationError,
    friendly_navigation_error,
    user_message_for,
)
from scanner.services.playwright_scanner import run_scan


class FriendlyNavigationErrorTests(TestCase):
    def test_dns_error_maps_to_not_found(self):
        exc = Exception('Page.goto: net::ERR_NAME_NOT_RESOLVED at https://does-not-exist.invalid/')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_DNS)

    def test_connection_refused_maps_to_connection_message(self):
        exc = Exception('Page.goto: net::ERR_CONNECTION_REFUSED at https://localhost:9/')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_CONNECTION)

    def test_connection_reset_maps_to_connection_message(self):
        exc = Exception('Page.goto: net::ERR_CONNECTION_RESET at https://example.com/')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_CONNECTION)

    def test_connection_timed_out_maps_to_timeout_message(self):
        exc = Exception('Page.goto: net::ERR_CONNECTION_TIMED_OUT at https://example.com/')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_TIMEOUT)

    def test_playwright_timeout_maps_to_timeout_message(self):
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        exc = PlaywrightTimeoutError('Page.goto: Timeout 30000ms exceeded.')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_TIMEOUT)

    def test_navigation_timeout_text_maps_to_timeout_message(self):
        exc = Exception('Page.goto: Timeout 30000ms exceeded. Call log: ...')
        self.assertEqual(friendly_navigation_error(exc), MESSAGE_TIMEOUT)

    def test_unknown_error_maps_to_generic_message(self):
        self.assertEqual(friendly_navigation_error(Exception('kaboom')), MESSAGE_GENERIC)

    def test_dns_is_not_reported_as_connection(self):
        exc = Exception('net::ERR_NAME_NOT_RESOLVED')
        self.assertNotEqual(friendly_navigation_error(exc), MESSAGE_CONNECTION)

    def test_failed_messages_never_contain_raw_error_codes(self):
        exc = Exception('Page.goto: net::ERR_NAME_NOT_RESOLVED at https://x.invalid/')
        message = friendly_navigation_error(exc)
        self.assertNotIn('net::', message)
        self.assertNotIn('ERR_', message)


class UserMessageTests(TestCase):
    def test_navigation_error_uses_its_user_message(self):
        self.assertEqual(user_message_for(ScanNavigationError(MESSAGE_DNS)), MESSAGE_DNS)

    def test_validation_value_error_is_preserved(self):
        message = 'Private or unsafe URLs are not allowed'
        self.assertEqual(user_message_for(ValueError(message)), message)

    def test_unknown_exception_is_generic(self):
        exc = Exception('Page.goto: net::ERR_NAME_NOT_RESOLVED at https://x.invalid/')
        self.assertEqual(user_message_for(exc), MESSAGE_GENERIC)


class ScanFailureApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('scanner.views.run_scan')
    def test_navigation_failure_returns_friendly_message(self, mock_run):
        mock_run.side_effect = ScanNavigationError(MESSAGE_DNS)
        resp = self.client.post(
            '/api/scans/', {'url': 'https://does-not-exist.invalid'}, format='json'
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data['error'], MESSAGE_DNS)
        self.assertNotIn('net::', resp.data['error'])
        scan = Scan.objects.get(id=resp.data['scan_id'])
        self.assertEqual(scan.status, Scan.FAILED)
        self.assertEqual(scan.error_message, MESSAGE_DNS)
        self.assertIsNone(scan.score)

    @patch('scanner.views.run_scan')
    def test_unexpected_failure_does_not_leak_raw_error(self, mock_run):
        mock_run.side_effect = Exception(
            'Page.goto: net::ERR_NAME_NOT_RESOLVED at https://x.invalid/'
        )
        resp = self.client.post('/api/scans/', {'url': 'https://x.invalid'}, format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data['error'], MESSAGE_GENERIC)
        self.assertNotIn('ERR_NAME_NOT_RESOLVED', resp.data['error'])
        scan = Scan.objects.get(id=resp.data['scan_id'])
        self.assertEqual(scan.status, Scan.FAILED)
        self.assertIsNone(scan.score)

    @patch('scanner.views.run_scan')
    def test_validation_error_message_is_preserved(self, mock_run):
        message = 'Private or unsafe URLs are not allowed'
        mock_run.side_effect = ValueError(message)
        resp = self.client.post(
            '/api/scans/', {'url': 'http://127.0.0.1'}, format='json'
        )
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data['error'], message)


class ScanCreateDatabaseFailureTests(TestCase):
    """Regression: the queue write runs before Playwright, so a database
    failure there raised out of the view as an opaque Django 500 with no
    server-side traceback. The view must log the full exception and answer
    with a generic message that does not leak the database error.
    """

    def setUp(self):
        self.client = APIClient()

    @patch('scanner.views.Scan.objects.create')
    def test_database_error_on_create_is_logged_without_leaking(self, mock_create):
        mock_create.side_effect = OperationalError(
            'relation "scanner_scan" does not exist'
        )
        with self.assertLogs('scanner.views', level='ERROR') as captured:
            resp = self.client.post(
                '/api/scans/', {'url': 'https://example.com'}, format='json'
            )

        self.assertEqual(resp.status_code, 500)
        body = str(resp.data)
        self.assertNotIn('scanner_scan', body)
        self.assertNotIn('relation', body.lower())
        self.assertIn('scanner_scan', '\n'.join(captured.output))


class ScanMissingChromiumTests(TestCase):
    """Regression: production containers only pip-install the Playwright
    package; unless the build runs `playwright install chromium`,
    p.chromium.launch() raises "Executable doesn't exist ... playwright
    install" within a few hundred ms of Scan.objects.create(). The pipeline
    must log that traceback server-side, mark the scan FAILED with a score
    of None, and keep the raw Playwright text out of the record and API.
    """

    LAUNCH_ERROR = (
        'BrowserType.launch: Executable doesn\'t exist at '
        '/root/.cache/ms-playwright/chromium_headless_shell-1243/'
        'chrome-headless-shell-linux64/chrome-headless-shell\n'
        'Please run the following command to download new browsers:\n'
        '    playwright install'
    )

    @patch('scanner.services.playwright_scanner.sync_playwright')
    def test_missing_browser_binary_fails_scan_safely(self, mock_sync_playwright):
        class FailingBrowserType:
            def launch(self, **kwargs):
                raise Exception(ScanMissingChromiumTests.LAUNCH_ERROR)

        class FakePlaywright:
            chromium = FailingBrowserType()

        mock_sync_playwright.return_value.__enter__.return_value = FakePlaywright()

        scan = Scan.objects.create(url='https://example.com', status=Scan.QUEUED)
        with self.assertLogs('scanner.services.playwright_scanner', level='ERROR') as logs:
            with self.assertRaises(Exception) as ctx:
                run_scan(scan.id)

        self.assertIn('Executable doesn\'t exist', '\n'.join(logs.output))
        self.assertIn('playwright install', '\n'.join(logs.output))

        scan.refresh_from_db()
        self.assertEqual(scan.status, Scan.FAILED)
        self.assertEqual(scan.error_message, MESSAGE_GENERIC)
        self.assertIsNone(scan.score)
        self.assertIsNotNone(scan.completed_at)
        self.assertNotIn('ms-playwright', scan.error_message)
        self.assertEqual(user_message_for(ctx.exception), MESSAGE_GENERIC)


class DeploymentConfigTests(TestCase):
    """Regression: Railpack only copies whitelisted paths (/app/.venv, /app)
    from a build step into the deploy image, so browsers downloaded by a
    custom buildCommand to /root/.cache/ms-playwright never reached the
    runtime container ("Executable doesn't exist at
    /root/.cache/ms-playwright/..."). The backend image must therefore be
    built from the Dockerfile, which installs Chromium into the stable
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright inside the same single image
    that serves Django, while Railway's gunicorn start command and the
    migrate pre-deploy command stay unchanged.
    """

    BACKEND_DIR = Path(__file__).resolve().parents[1]

    def test_dockerfile_installs_chromium_at_stable_browsers_path(self):
        dockerfile = (self.BACKEND_DIR / 'Dockerfile').read_text()
        self.assertIn('ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright', dockerfile)
        self.assertIn('python -m playwright install --with-deps chromium', dockerfile)
        # The install must run in the same stage as the app, after the pinned
        # requirements, so the browser revision always matches the runtime
        # playwright package.
        self.assertIn('pip install --no-cache-dir -r requirements.txt', dockerfile)
        self.assertIn('FROM python:3.13-slim', dockerfile)
        # Railway runs a custom start command without a shell, so gunicorn's
        # args must go through sh -c or $PORT arrives literal and gunicorn
        # dies with "'$PORT' is not a valid port number".
        self.assertIn('CMD ["sh", "-c", "gunicorn config.wsgi:application', dockerfile)
        self.assertIn('--bind 0.0.0.0:${PORT}', dockerfile)

    def test_railway_config_keeps_gunicorn_and_migrations(self):
        import json

        config = json.loads((self.BACKEND_DIR / 'railway.json').read_text())
        deploy = config['deploy']
        self.assertEqual(
            deploy['startCommand'],
            'sh -c "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} '
            '--workers 1 --threads 2 --timeout 300"',
        )
        self.assertEqual(deploy['preDeployCommand'], 'python manage.py migrate --noinput')
        # A buildCommand here would be ignored with a Dockerfile present and
        # previously caused the browsers to be dropped from the image.
        self.assertNotIn('build', config)

    def test_requirements_pin_playwright_for_revision_match(self):
        requirements = (self.BACKEND_DIR / 'requirements.txt').read_text()
        self.assertIn('playwright==', requirements)

