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

