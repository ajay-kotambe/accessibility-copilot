"""NVIDIA NIM integration for the accessibility Copilot.

Division of responsibility
--------------------------
Detection is deterministic and stays in the scanner: Playwright drives
Chromium, axe-core evaluates the live page, and ``scoring.py`` computes the
score. This module is only reached afterwards, when a developer asks for help
with an issue that already exists in the database. NVIDIA NIM explains and
repairs findings; it is never asked whether a violation exists.

The API key is read here, on the Django backend, and is never returned by any
serializer, view or error message.
"""

import json
import logging
import os
import time

import openai
from django.conf import settings
from openai import OpenAI

from .prompts import EXPLAIN_ISSUE_PROMPT, FIX_ISSUE_PROMPT, SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

# OpenAI-compatible endpoint for NVIDIA NIM. The backend reaches it through the
# OpenAI v1.x client; the key stays server-side and is never sent to browsers.
NVIDIA_BASE_URL = 'https://integrate.api.nvidia.com/v1'
DEFAULT_MODEL = 'moonshotai/kimi-k3'
REQUEST_TIMEOUT_SECONDS = 60
MAX_OUTPUT_TOKENS = 4096

# Rate limits, capacity spikes and read timeouts are transient and were
# observed on roughly half of live calls, so they are retried before the
# developer is shown an error for a condition that clears on its own.
RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

GENERIC_ERROR = 'AI analysis is temporarily unavailable. Please try again.'
NOT_CONFIGURED = 'AI analysis is not configured on the server.'
QUOTA_EXCEEDED = 'AI usage limit reached for now. Please try again later.'

RESPONSE_FIELDS = (
    'explanation',
    'why_it_matters',
    'suggested_fix',
    'corrected_code',
    'developer_tip',
)

# Ordered prefix -> field, used only if the model replies with prose instead of
# JSON (for example if structured output is unavailable for the model).
_SECTION_ALIASES = {
    'explanation': 'explanation',
    'why it matters': 'why_it_matters',
    'why this matters': 'why_it_matters',
    'suggested fix': 'suggested_fix',
    'fix': 'suggested_fix',
    'corrected code': 'corrected_code',
    'corrected html': 'corrected_code',
    'code': 'corrected_code',
    'developer tip': 'developer_tip',
    'tip': 'developer_tip',
}


class AIServiceError(Exception):
    """An NVIDIA NIM-side failure.

    ``reason`` is for server logs only and may name the provider, the status
    code or the model. ``user_message`` is the only text safe to send to a
    browser: it never contains the API key, a URL with a key in it, or a
    traceback.
    """

    def __init__(self, reason, user_message=GENERIC_ERROR):
        super().__init__(reason)
        self.reason = reason
        self.user_message = user_message


def _setting(name):
    """Read from Django settings first, then fall back to the environment."""
    value = getattr(settings, name, None)
    return value or os.getenv(name)


class AIService:
    def __init__(self, api_key=None, model=None):
        self.api_key = api_key if api_key is not None else _setting('NVIDIA_API_KEY')
        self.model = model or _setting('NVIDIA_MODEL') or DEFAULT_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self):
        key = (self.api_key or '').strip()
        if not key:
            raise AIServiceError('NVIDIA_API_KEY is not set', NOT_CONFIGURED)
        try:
            return OpenAI(
                api_key=key,
                base_url=NVIDIA_BASE_URL,
                timeout=REQUEST_TIMEOUT_SECONDS,
                # Retries are handled explicitly in ``_generate``; disabling
                # the SDK's implicit retries keeps that the single source of
                # truth instead of multiplying attempts.
                max_retries=0,
            )
        except ValueError as exc:
            raise AIServiceError(f'NVIDIA NIM client rejected the key: {exc}', NOT_CONFIGURED) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise AIServiceError(f'NVIDIA NIM client init failed: {exc}') from exc

    @staticmethod
    def _issue_context(issue):
        return {
            'rule_id': issue.rule_id,
            'severity': issue.severity,
            'impact': issue.impact or 'not stated',
            'category': issue.category or 'not categorised',
            'description': issue.description or '',
            'selector': issue.selector or '(no selector reported)',
            'help_url': issue.help_url or '(no reference URL reported)',
            'html_snippet': (issue.html_snippet or '(no markup reported)').strip(),
        }

    def _generate(self, prompt):
        """Call NVIDIA NIM and return the raw text of its reply.

        Transient provider conditions are retried; configuration problems are
        not, because repeating a missing API key only delays the real error.
        """
        messages = [
            {'role': 'system', 'content': SYSTEM_INSTRUCTION},
            {'role': 'user', 'content': prompt},
        ]

        for attempt in range(1, MAX_ATTEMPTS + 1):
            last = attempt == MAX_ATTEMPTS
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    response_format={'type': 'json_object'},
                )
            except AIServiceError:
                # Raised by the `client` property when the key is missing or
                # rejected. Not retryable, and not an API failure.
                raise
            except openai.APIStatusError as exc:
                error = self._translate(exc)
                if last or not self._is_retryable(exc):
                    raise error from exc
                logger.warning('NVIDIA NIM attempt %s/%s failed (%s); retrying',
                               attempt, MAX_ATTEMPTS, error.reason)
            except openai.APITimeoutError as exc:
                if last:
                    raise AIServiceError(f'NVIDIA NIM request timed out: {exc}') from exc
                logger.warning('NVIDIA NIM attempt %s/%s timed out; retrying', attempt, MAX_ATTEMPTS)
            except openai.OpenAIError as exc:
                # Other client-side failures, including connection errors.
                timed_out = ('timeout' in type(exc).__name__.lower()
                             or 'timeout' in str(exc).lower())
                if last or not timed_out:
                    raise AIServiceError(
                        f'NVIDIA NIM request failed: {type(exc).__name__}: {exc}') from exc
                logger.warning('NVIDIA NIM attempt %s/%s timed out (%s); retrying',
                               attempt, MAX_ATTEMPTS, type(exc).__name__)
            else:
                text = self._reply_text(response)
                if not text:
                    raise AIServiceError('NVIDIA NIM returned an empty response body')
                return text

            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise AIServiceError('NVIDIA NIM request failed after retries')  # pragma: no cover

    @staticmethod
    def _reply_text(response):
        """Extract the assistant message text from a chat completion."""
        choices = getattr(response, 'choices', None) or []
        if not choices:
            return None
        message = getattr(choices[0], 'message', None)
        return getattr(message, 'content', None)

    @staticmethod
    def _status_code(exc):
        """Read the HTTP status from an OpenAI-compatible SDK exception."""
        code = getattr(exc, 'status_code', None)
        if code is None:
            code = getattr(exc, 'code', None)
        try:
            return int(code or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _is_quota_exhausted(exc):
        """Tell an exhausted account quota from a transient rate limit.

        Rate limits and hard quota exhaustion can both arrive as HTTP 429, but
        retrying an exhausted quota only adds latency to an error the developer
        cannot clear by waiting, so it must not be treated as transient.
        """
        detail = (getattr(exc, 'message', None) or str(exc)).lower()
        return 'quota exceeded' in detail or 'exceeded your current quota' in detail

    @classmethod
    def _is_retryable(cls, exc):
        """True only for provider conditions that clear without user action."""
        if cls._is_quota_exhausted(exc):
            return False
        return cls._status_code(exc) in RETRYABLE_CODES

    def _translate(self, exc):
        """Map a provider exception onto a clean, loggable AIServiceError."""
        code = self._status_code(exc)
        detail = (getattr(exc, 'message', None) or str(exc))[:300]
        if code in (401, 403):
            return AIServiceError(f'NVIDIA NIM rejected the API key (HTTP {code}): {detail}', NOT_CONFIGURED)
        if code == 404:
            return AIServiceError(f'NVIDIA NIM model unavailable (HTTP 404): {detail}')
        if code == 429:
            if self._is_quota_exhausted(exc):
                return AIServiceError(f'NVIDIA NIM quota exhausted (HTTP 429): {detail}',
                                      QUOTA_EXCEEDED)
            return AIServiceError(f'NVIDIA NIM rate limit (HTTP 429): {detail}')
        if code == 400:
            return AIServiceError(f'NVIDIA NIM rejected the request (HTTP 400): {detail}')
        if code >= 500:
            return AIServiceError(f'NVIDIA NIM server error (HTTP {code}): {detail}')
        return AIServiceError(f'NVIDIA NIM API error (HTTP {code}): {detail}')

    @staticmethod
    def _strip_fence(value):
        """Unwrap a markdown fence if the model added one anyway."""
        text = (value or '').strip()
        if '```' not in text:
            return text
        parts = text.split('```')
        if len(parts) < 2:
            return text.replace('```', '').strip()

        body = parts[1]
        # Drop an optional language tag on the fence's opening line. Detect it
        # by shape rather than by a fixed length, since tags vary ("html",
        # "HTML", "xml", "jsx", ...).
        first_line, newline, rest = body.partition('\n')
        if newline and not any(ch in first_line for ch in '<>{}'):
            body = rest
        return body.strip()

    @classmethod
    def _normalize(cls, raw):
        """Coerce a model reply into the five-field contract.

        Raises AIServiceError rather than storing a half-empty brief, so the
        UI never shows an AI panel with invented or missing content.
        """
        parsed = None

        text = (raw or '').strip()
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            parsed = None

        if not isinstance(parsed, dict):
            # The model may have wrapped the JSON in prose or a markdown fence.
            # Try the outermost {...} span before giving up on structured output.
            start, end = text.find('{'), text.rfind('}')
            if start != -1 and end > start:
                try:
                    parsed = json.loads(text[start:end + 1])
                except (TypeError, ValueError):
                    parsed = None

        if not isinstance(parsed, dict):
            parsed = cls._parse_sections(text)

        if parsed is None:
            raise AIServiceError(f'NVIDIA NIM response was not usable: {text[:200]!r}')

        result = {}
        for field in RESPONSE_FIELDS:
            value = parsed.get(field, '')
            if not isinstance(value, str):
                value = '' if value is None else str(value)
            result[field] = value.strip()

        result['corrected_code'] = cls._strip_fence(result['corrected_code'])

        if not any(result.values()):
            raise AIServiceError('NVIDIA NIM returned an empty brief')
        return result

    @staticmethod
    def _looks_like_prose(text):
        """Guard the unstructured fallback so junk is never stored as a brief.

        Anything short, markup-shaped, or scalar is rejected rather than being
        filed under "explanation".
        """
        stripped = (text or '').strip()
        if len(stripped) < 80:
            return False
        if stripped.startswith(('<', '{', '[')):
            return False
        return True

    @classmethod
    def _parse_sections(cls, text):
        """Fallback parser for a prose reply with numbered headings."""
        collected = {}
        current = None
        for line in text.splitlines():
            lowered = line.strip().lower().rstrip(':')
            cleaned = lowered.lstrip('0123456789. ').strip()
            if cleaned in _SECTION_ALIASES:
                current = _SECTION_ALIASES[cleaned]
                continue
            if current:
                collected[current] = collected.get(current, '') + line + '\n'
        if collected:
            return collected
        # A single unstructured paragraph is only usable if it reads like prose.
        if cls._looks_like_prose(text):
            return {'explanation': text}
        return None

    # Public API used by the views -------------------------------------------------

    def analyze_issue(self, issue):
        prompt = EXPLAIN_ISSUE_PROMPT.format(**self._issue_context(issue))
        return self._normalize(self._generate(prompt))

    def generate_fix(self, issue):
        prompt = FIX_ISSUE_PROMPT.format(**self._issue_context(issue))
        return self._normalize(self._generate(prompt))
