"""Gemini integration for the accessibility Copilot.

Division of responsibility
--------------------------
Detection is deterministic and stays in the scanner: Playwright drives
Chromium, axe-core evaluates the live page, and ``scoring.py`` computes the
score. This module is only reached afterwards, when a developer asks for help
with an issue that already exists in the database. Gemini explains and repairs
findings; it is never asked whether a violation exists.

The API key is read here, on the Django backend, and is never returned by any
serializer, view or error message.
"""

import json
import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types
from google.genai.errors import APIError

from .prompts import EXPLAIN_ISSUE_PROMPT, FIX_ISSUE_PROMPT, SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'gemini-3.8-flash'
REQUEST_TIMEOUT_MS = 60_000
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

# Gemini returns JSON against this schema instead of free-form markdown, so the
# five fields the frontend expects arrive under predictable keys.
RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'explanation': {'type': 'STRING'},
        'why_it_matters': {'type': 'STRING'},
        'suggested_fix': {'type': 'STRING'},
        'corrected_code': {'type': 'STRING'},
        'developer_tip': {'type': 'STRING'},
    },
    'required': list(RESPONSE_FIELDS),
}

# Ordered prefix -> field, used only if Gemini replies with prose instead of
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
    """A Gemini-side failure.

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
        self.api_key = api_key if api_key is not None else _setting('GEMINI_API_KEY')
        self.model = model or _setting('GEMINI_MODEL') or DEFAULT_MODEL
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self):
        key = (self.api_key or '').strip()
        if not key:
            raise AIServiceError('GEMINI_API_KEY is not set', NOT_CONFIGURED)
        try:
            return genai.Client(api_key=key)
        except ValueError as exc:
            # google-genai validates key presence on construction.
            raise AIServiceError(f'Gemini client rejected the key: {exc}', NOT_CONFIGURED) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise AIServiceError(f'Gemini client init failed: {exc}') from exc

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
        """Call Gemini and return the raw text of its reply.

        Transient provider conditions are retried; configuration problems are
        not, because repeating a missing API key only delays the real error.
        """
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            response_mime_type='application/json',
            response_schema=RESPONSE_SCHEMA,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )

        for attempt in range(1, MAX_ATTEMPTS + 1):
            last = attempt == MAX_ATTEMPTS
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
            except AIServiceError:
                # Raised by the `client` property when the key is missing or
                # rejected. Not retryable, and not an API failure.
                raise
            except APIError as exc:
                error = self._translate(exc)
                if last or not self._is_retryable(exc):
                    raise error from exc
                logger.warning('Gemini attempt %s/%s failed (%s); retrying',
                               attempt, MAX_ATTEMPTS, error.reason)
            except TimeoutError as exc:
                if last:
                    raise AIServiceError(f'Gemini request timed out: {exc}') from exc
                logger.warning('Gemini attempt %s/%s timed out; retrying', attempt, MAX_ATTEMPTS)
            except Exception as exc:
                # httpx surfaces timeouts under its own type names.
                timed_out = ('timeout' in type(exc).__name__.lower()
                             or 'timeout' in str(exc).lower())
                if last or not timed_out:
                    raise AIServiceError(
                        f'Gemini request failed: {type(exc).__name__}: {exc}') from exc
                logger.warning('Gemini attempt %s/%s timed out (%s); retrying',
                               attempt, MAX_ATTEMPTS, type(exc).__name__)
            else:
                text = getattr(response, 'text', None)
                if not text:
                    raise AIServiceError('Gemini returned an empty response body')
                return text

            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise AIServiceError('Gemini request failed after retries')  # pragma: no cover

    @staticmethod
    def _is_quota_exhausted(exc):
        """Tell an exhausted account quota from a transient rate limit.

        Google answers both with HTTP 429, but retrying a hard quota exhaustion
        only adds latency to an error the developer cannot clear by waiting a
        few seconds, so it must not be treated as transient.
        """
        detail = (getattr(exc, 'message', None) or str(exc)).lower()
        return 'quota exceeded' in detail or 'exceeded your current quota' in detail

    @classmethod
    def _is_retryable(cls, exc):
        """True only for provider conditions that clear without user action."""
        if cls._is_quota_exhausted(exc):
            return False
        try:
            code = int(getattr(exc, 'code', None) or 0)
        except (TypeError, ValueError):
            return False
        return code in RETRYABLE_CODES

    def _translate(self, exc):
        """Map a provider exception onto a clean, loggable AIServiceError."""
        try:
            code = int(getattr(exc, 'code', None) or 0)
        except (TypeError, ValueError):
            code = 0
        detail = (getattr(exc, 'message', None) or str(exc))[:300]
        if code in (401, 403):
            return AIServiceError(f'Gemini rejected the API key (HTTP {code}): {detail}', NOT_CONFIGURED)
        if code == 404:
            return AIServiceError(f'Gemini model unavailable (HTTP 404): {detail}')
        if code == 429:
            if self._is_quota_exhausted(exc):
                return AIServiceError(f'Gemini quota exhausted (HTTP 429): {detail}',
                                      QUOTA_EXCEEDED)
            return AIServiceError(f'Gemini rate limit (HTTP 429): {detail}')
        if code == 400:
            return AIServiceError(f'Gemini rejected the request (HTTP 400): {detail}')
        if code >= 500:
            return AIServiceError(f'Gemini server error (HTTP {code}): {detail}')
        return AIServiceError(f'Gemini API error (HTTP {code}): {detail}')

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
        """Coerce a Gemini reply into the five-field contract.

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
            raise AIServiceError(f'Gemini response was not usable: {text[:200]!r}')

        result = {}
        for field in RESPONSE_FIELDS:
            value = parsed.get(field, '')
            if not isinstance(value, str):
                value = '' if value is None else str(value)
            result[field] = value.strip()

        result['corrected_code'] = cls._strip_fence(result['corrected_code'])

        if not any(result.values()):
            raise AIServiceError('Gemini returned an empty brief')
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