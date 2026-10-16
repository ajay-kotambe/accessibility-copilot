"""Regression tests for the NVIDIA NIM integration.

Production symptom: ``AI request failed for issue 20: NVIDIA NIM returned an
empty response body``. An HTTP 200 with missing/blank ``choices[0].message.content``
must be retried a bounded number of times, and a persistently empty reply must
fail only that one issue request with a generic message — never the scan,
never with the API key, and never with an invented brief.
"""

import json
import openai
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
    MAX_OUTPUT_TOKENS,
    MAX_OUTPUT_TOKENS_CAP,
    NVIDIA_BASE_URL,
    REASONING_BUDGET_TOKENS,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
)


def completion(content, finish_reason='stop', reasoning=None, reasoning_tokens=None):
    """A minimal OpenAI-compatible chat completion object.

    ``reasoning``/``reasoning_tokens`` model a reasoning model that spent part
    of its ``max_tokens`` allowance on a hidden trace before emitting content.
    """
    message = SimpleNamespace(content=content)
    if reasoning is not None:
        message.reasoning = reasoning
    usage = None
    if reasoning_tokens is not None:
        usage = SimpleNamespace(
            completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens)
        )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(finish_reason=finish_reason, message=message)
        ],
        usage=usage,
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
        self.assertEqual(
            client.chat.completions.create.call_args.kwargs['max_tokens'],
            MAX_OUTPUT_TOKENS,
        )
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
            [call(RETRY_BACKOFF_SECONDS * n) for n in range(1, MAX_ATTEMPTS)]
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
    def test_length_truncated_empty_reply_escalates_token_budget(self, mock_sleep):
        # Production symptom: a reasoning model spends the whole 16384-token
        # allowance on its hidden trace, so the reply is content=null with
        # finish_reason=length. The next attempt must request more room within
        # the model's documented cap instead of repeating the same budget.
        truncated = completion(
            None, finish_reason='length',
            reasoning='x' * 120, reasoning_tokens=MAX_OUTPUT_TOKENS,
        )
        service, client = make_service(truncated, completion(VALID_BRIEF))

        with self.assertLogs('ai.services', level='WARNING') as logs:
            result = service.analyze_issue(self.issue)

        self.assertEqual(result['explanation'], 'The image has no alt text.')
        self.assertEqual(client.chat.completions.create.call_count, 2)
        budgets = [
            c.kwargs['max_tokens'] for c in client.chat.completions.create.call_args_list
        ]
        self.assertEqual(budgets[0], MAX_OUTPUT_TOKENS)
        self.assertEqual(budgets[1], min(MAX_OUTPUT_TOKENS * 2, MAX_OUTPUT_TOKENS_CAP))
        self.assertGreater(budgets[1], budgets[0])

        output = '\n'.join(logs.output)
        self.assertIn('finish_reason=length', output)
        self.assertIn('reasoning_length=120', output)
        self.assertIn(f'reasoning_tokens={MAX_OUTPUT_TOKENS}', output)
        self.assertIn(f'max_tokens={budgets[1]}', output)
        self.assertNotIn('unit-test-key', output)

    @patch('ai.services.time.sleep')
    def test_persistent_length_truncation_fails_with_token_budget_diagnostic(self, mock_sleep):
        truncated = completion(
            None, finish_reason='length',
            reasoning='x' * 40, reasoning_tokens=MAX_OUTPUT_TOKENS,
        )
        service, client = make_service(truncated, truncated, truncated)

        with self.assertRaises(AIServiceError) as ctx:
            service.analyze_issue(self.issue)

        self.assertEqual(client.chat.completions.create.call_count, MAX_ATTEMPTS)
        budgets = [
            c.kwargs['max_tokens'] for c in client.chat.completions.create.call_args_list
        ]
        self.assertEqual(budgets[0], MAX_OUTPUT_TOKENS)
        self.assertEqual(budgets[-1], MAX_OUTPUT_TOKENS_CAP)
        self.assertTrue(all(b <= MAX_OUTPUT_TOKENS_CAP for b in budgets))

        reason = ctx.exception.reason
        self.assertIn('empty response body', reason)
        self.assertIn('finish_reason=length', reason)
        self.assertIn('reasoning_length=40', reason)
        self.assertEqual(ctx.exception.user_message, GENERIC_ERROR)

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


class AITimeoutTests(AIBaseTestCase):
    """Production symptom: ``NVIDIA NIM request timed out`` on every attempt.

    A slow provider must be retried a bounded number of times, then fail only
    the one issue request with a generic message — never the scan, never with
    the API key, and never blocking other issues.
    """

    @staticmethod
    def _timeout():
        return openai.APITimeoutError(request=MagicMock())

    @patch('ai.services.time.sleep')
    def test_timeout_is_retried_then_succeeds(self, mock_sleep):
        service, client = make_service(self._timeout(), completion(VALID_BRIEF))

        with self.assertLogs('ai.services', level='WARNING') as logs:
            result = service.analyze_issue(self.issue)

        self.assertEqual(result['explanation'], 'The image has no alt text.')
        self.assertEqual(client.chat.completions.create.call_count, 2)
        mock_sleep.assert_called_once_with(RETRY_BACKOFF_SECONDS * 1)
        output = '\n'.join(logs.output)
        self.assertIn('timed out', output)
        self.assertIn('test/model', output)
        self.assertNotIn('unit-test-key', output)

    @patch('ai.services.time.sleep')
    def test_persistent_timeout_stops_after_max_attempts(self, mock_sleep):
        service, client = make_service(
            self._timeout(), self._timeout(), self._timeout()
        )

        with self.assertRaises(AIServiceError) as ctx:
            service.analyze_issue(self.issue)

        self.assertEqual(client.chat.completions.create.call_count, MAX_ATTEMPTS)
        self.assertEqual(mock_sleep.call_count, MAX_ATTEMPTS - 1)
        self.assertIn('timed out', ctx.exception.reason)
        self.assertEqual(ctx.exception.user_message, GENERIC_ERROR)

    @patch('ai.services.time.sleep')
    def test_endpoint_timeout_is_graceful_and_keeps_scan_and_other_issues(self, mock_sleep):
        service, _ = make_service(self._timeout(), self._timeout(), self._timeout())
        api = APIClient()

        with patch('ai.views.AIService', return_value=service):
            with self.assertLogs('ai.views', level='WARNING') as logs:
                resp = api.post(f'/api/issues/{self.issue.id}/analyze/', format='json')

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.data['detail'], GENERIC_ERROR)
        self.assertNotIn('timed out', str(resp.data))
        self.assertIn('timed out', '\n'.join(logs.output))

        # A timeout must not invalidate the deterministic scan result or
        # invent a half-empty AI brief.
        self.scan.refresh_from_db()
        self.assertEqual(self.scan.status, Scan.COMPLETED)
        self.assertEqual(self.scan.score, 87)
        self.assertFalse(AIAnalysis.objects.filter(issue=self.issue).exists())

        # The timeout on one issue must not prevent another issue from working.
        other = Issue.objects.create(
            scan=self.scan, rule_id='button-name', severity=Issue.SERIOUS,
            category='Forms', description='Buttons must have discernible text',
        )
        good, _ = make_service(completion(VALID_BRIEF))
        with patch('ai.views.AIService', return_value=good):
            resp2 = api.post(f'/api/issues/{other.id}/analyze/', format='json')
        self.assertEqual(resp2.status_code, 200)
        self.assertTrue(AIAnalysis.objects.filter(issue=other).exists())


class AIRequestConfigurationTests(TestCase):
    def test_total_worst_case_wait_is_bounded(self):
        # Attempts and timeout together are the ceiling. MAX_ATTEMPTS stays at
        # 2 and the backoff stays short so a persistently slow provider cannot
        # hold a request for minutes.
        worst_case = (
            REQUEST_TIMEOUT_SECONDS * MAX_ATTEMPTS
            + RETRY_BACKOFF_SECONDS * (MAX_ATTEMPTS - 1)
        )
        self.assertEqual(MAX_ATTEMPTS, 2)
        self.assertLessEqual(RETRY_BACKOFF_SECONDS, 2)
        self.assertLessEqual(REQUEST_TIMEOUT_SECONDS, 45)
        self.assertLessEqual(worst_case, REQUEST_TIMEOUT_SECONDS * MAX_ATTEMPTS + 2)

    def test_output_budget_is_sized_for_a_single_issue(self):
        self.assertEqual(MAX_OUTPUT_TOKENS, 1024)
        self.assertEqual(MAX_OUTPUT_TOKENS_CAP, 2048)

    def test_reasoning_trace_is_capped_below_the_output_budget(self):
        # The visible answer must keep room inside max_tokens; otherwise the
        # thinking trace consumes the whole allowance and the reply is empty.
        self.assertEqual(REASONING_BUDGET_TOKENS, 256)
        self.assertGreater(REASONING_BUDGET_TOKENS, 0)
        self.assertLess(REASONING_BUDGET_TOKENS, MAX_OUTPUT_TOKENS)

    def test_reasoning_budget_is_sent_as_extra_body(self):
        # `reasoning_budget` is the field the hosted integrate.api.nvidia.com
        # endpoint accepts and honours for `nvidia/nemotron-3.5-lightning`.
        params = AIService._extra_request_params()
        self.assertEqual(
            params,
            {'extra_body': {'reasoning_budget': REASONING_BUDGET_TOKENS}},
        )
        self.assertNotIn('thinking_token_budget', params['extra_body'])

    def test_reasoning_control_is_optional(self):
        with patch('ai.services.REASONING_BUDGET_TOKENS', 0):
            self.assertEqual(AIService._extra_request_params(), {})


class AIRequestVerificationTests(AIBaseTestCase):
    """The request actually sent must carry the configured budget and timeout.

    A smaller ``max_tokens`` only bounds the visible answer. Unless the hidden
    reasoning trace is capped with the model-supported field, reducing
    ``max_tokens`` does not reduce reasoning.
    """

    @patch('ai.services.time.sleep')
    def test_request_sends_configured_tokens_and_reasoning_budget(self, mock_sleep):
        service, client = make_service(completion(VALID_BRIEF))

        service.analyze_issue(self.issue)

        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs['max_tokens'], MAX_OUTPUT_TOKENS)
        self.assertEqual(kwargs['extra_body']['reasoning_budget'],
                         REASONING_BUDGET_TOKENS)
        self.assertNotIn('thinking_token_budget', kwargs['extra_body'])
        self.assertEqual(kwargs['response_format'], {'type': 'json_object'})

    @patch('ai.services.OpenAI')
    def test_client_is_built_with_the_configured_timeout(self, mock_openai):
        AIService(api_key='unit-test-key').client

        kwargs = mock_openai.call_args.kwargs
        self.assertEqual(kwargs['timeout'], REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(kwargs['base_url'], NVIDIA_BASE_URL)
        self.assertEqual(kwargs['max_retries'], 0)
        self.assertNotIn('unit-test-key', str(kwargs.get('base_url', '')))


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
