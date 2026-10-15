"""Regression tests for the NVIDIA NIM integration.

Production symptom: ``AI request failed for issue 20: NVIDIA NIM returned an
empty response body``. An HTTP 200 with missing/blank ``choices[0].message.content``
must be retried a bounded number of times, and a persistently empty reply must
fail only that one issue request with a generic message — never the scan,
never with the API key, and never with an invented brief.
"""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from scanner.models import AIAnalysis, Issue, Scan

from .services import (
    AIService,
    AIServiceError,
    GENERIC_ERROR,
    MAX_ATTEMPTS,
    RETRY_BACKOFF_SECONDS,
)


def completion(content, finish_reason='stop'):
    """A minimal OpenAI-compatible chat completion object."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content),
            )
        ]
    )


VALID_BRIEF = json.dumps(
    {
        'explanation': 'The image has no alt text.',
        'why_it_matters': 'Screen reader users cannot tell what it shows.',
        'suggested_fix': 'Add an alt attribute describing the image.',
        'corrected_code': '<img src="photo.png" alt="Team photo">',
        'developer_tip': 'Keep alt text under 125 characters.',
    }
)


def make_service(*replies):
    """AIService wired to a fake client returning the given completions."""
    service = AIService(api_key='unit-test-key', model='test/model')
    client = MagicMock()
    client.chat.completions.create.side_effect = list(replies)
    service._client = client
    return service, client


class AIBaseTestCase(TestCase):
    def setUp(self):
        scan = Scan.objects.create(url='https://example.com', status=Scan.COMPLETED, score=87)
        self.scan = scan
        self.issue = Issue.objects.create(
            scan=scan,
            rule_id='image-alt',
            severity=Issue.CRITICAL,
            category='Images',
            description='Images must have alternate text',
            selector='img.logo',
            impact='critical',
        )


class AISuccessTests(AIBaseTestCase):
    @patch('ai.services.time.sleep')
    def test_successful_response_is_parsed_without_retry(self, mock_sleep):
        service, client = make_service(completion(VALID_BRIEF))

        result = service.analyze_issue(self.issue)

        self.assertEqual(result['explanation'], 'The image has no alt text.')
        self.assertEqual(result['corrected_code'], '<img src="photo.png" alt="Team photo">')
        for field in ('explanation', 'why_it_matters', 'suggested_fix', 'corrected_code'):
            self.assertTrue(result[field])
        self.assertEqual(client.chat.completions.create.call_count, 1)
        mock_sleep.assert_not_called()

    @patch('ai.services.time.sleep')
    def test_endpoint_persists_successful_analysis(self, mock_sleep):
        service, _ = make_service(completion(VALID_BRIEF))
        client = APIClient()
        with patch('ai.views.AIService', return_value=service):
            resp = client.post(f'/api/issues/{self.issue.id}/analyze/', format='json')

        self.assertEqual(resp.status_code, 200)
        analysis = AIAnalysis.objects.get(issue=self.issue)
        self.assertEqual(analysis.explanation, 'The image has no alt text.')
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.status, Scan.COMPLETED)
        self.assertEqual(self.scan.score, 87)
        mock_sleep.assert_not_called()


class AIEmptyResponseTests(AIBaseTestCase):
    @patch('ai.services.time.sleep')
    def test_empty_response_is_retried_with_bounded_backoff_then_succeeds(self, mock_sleep):
        service, client = make_service(completion(''), completion(VALID_BRIEF))

        with self.assertLogs('ai.services', level='WARNING') as logs:
            result = service.analyze_issue(self.issue)

        self.assertEqual(result['explanation'], 'The image has no alt text.')
        self.assertEqual(client.chat.completions.create.call_count, 2)
        mock_sleep.assert_called_once_with(RETRY_BACKOFF_SECONDS * 1)
        output = '\n'.join(logs.output)
        self.assertIn('empty reply', output)
        self.assertIn('test/model', output)
        self.assertNotIn('unit-test-key', output)

    @patch('ai.services.time.sleep')
    def test_whitespace_only_content_counts_as_empty(self, mock_sleep):
        service, client = make_service(completion('   \n  '), completion(VALID_BRIEF))

        result = service.analyze_issue(self.issue)

        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertTrue(result['explanation'])

    @patch('ai.services.time.sleep')
    def test_missing_choices_counts_as_empty(self, mock_sleep):
        service, client = make_service(
            SimpleNamespace(choices=[]), completion(VALID_BRIEF)
        )

        result = service.analyze_issue(self.issue)

        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertTrue(result['explanation'])

    @patch('ai.services.time.sleep')
    def test_persistent_empty_response_stops_after_max_attempts(self, mock_sleep):
        empty = completion('', finish_reason='length')
        service, client = make_service(empty, empty, empty)

        with self.assertLogs('ai.services', level='WARNING') as logs:
            with self.assertRaises(AIServiceError) as ctx:
                service.analyze_issue(self.issue)

        self.assertEqual(client.chat.completions.create.call_count, MAX_ATTEMPTS)
        self.assertEqual(mock_sleep.call_count, MAX_ATTEMPTS - 1)
        mock_sleep.assert_has_calls(
            [call(RETRY_BACKOFF_SECONDS * 1), call(RETRY_BACKOFF_SECONDS * 2)]
        )

        reason = ctx.exception.reason
        self.assertIn('empty response body', reason)
        self.assertIn('test/model', reason)
        self.assertIn('finish_reason=length', reason)
        self.assertEqual(ctx.exception.user_message, GENERIC_ERROR)

        logged = '\n'.join(logs.output)
        self.assertNotIn('unit-test-key', logged)
        self.assertNotIn('VALID_BRIEF', logged)

    @patch('ai.services.time.sleep')
    def test_endpoint_fails_one_issue_gracefully_and_keeps_scan_results(self, mock_sleep):
        empty = completion('')
        service, client = make_service(empty, empty, empty)
        api = APIClient()

        with patch('ai.views.AIService', return_value=service):
            with self.assertLogs('ai.views', level='WARNING') as logs:
                resp = api.post(f'/api/issues/{self.issue.id}/analyze/', format='json')

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.data['detail'], GENERIC_ERROR)
        self.assertNotIn('unit-test-key', str(resp.data))
        self.assertNotIn('empty response body', str(resp.data))
        self.assertIn('empty response body', '\n'.join(logs.output))

        # The deterministic scan result is untouched and no half-empty AI
        # brief is invented for the issue.
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.status, Scan.COMPLETED)
        self.assertEqual(self.scan.score, 87)
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.severity, Issue.CRITICAL)
        self.assertFalse(AIAnalysis.objects.filter(issue=self.issue).exists())

        # Other issues keep working: a later success on a second issue
        # still stores its brief.
        other = Issue.objects.create(
            scan=self.scan, rule_id='button-name', severity=Issue.SERIOUS,
            category='Forms', description='Buttons must have discernible text',
        )
        good, _ = make_service(completion(VALID_BRIEF))
        with patch('ai.views.AIService', return_value=good):
            resp2 = api.post(f'/api/issues/{other.id}/analyze/', format='json')
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(AIAnalysis.objects.filter(issue=other).exists())


class AIModelConfigurationTests(TestCase):
    @override_settings(NVIDIA_MODEL='')
    @patch.dict(os.environ, {'NVIDIA_MODEL': 'env-org/env-model'})
    def test_model_is_read_from_environment_when_setting_is_empty(self):
        self.assertEqual(AIService(api_key='k').model, 'env-org/env-model')

    @override_settings(NVIDIA_MODEL='settings/model')
    @patch.dict(os.environ, {'NVIDIA_MODEL': 'env-org/env-model'})
    def test_django_setting_takes_precedence_over_environment(self):
        self.assertEqual(AIService(api_key='k').model, 'settings/model')

    @override_settings(NVIDIA_MODEL='')
    @patch.dict(os.environ, {}, clear=False)
    def test_fallback_default_model_when_nothing_configured(self):
        os.environ.pop('NVIDIA_MODEL', None)
        from .services import DEFAULT_MODEL
        self.assertEqual(AIService(api_key='k').model, DEFAULT_MODEL)
