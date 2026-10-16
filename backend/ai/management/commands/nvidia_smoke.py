"""Minimal local smoke test for the NVIDIA NIM integration.

Sends exactly one accessibility request using the same model, timeout, token
budget and reasoning parameters as production, then prints the outcome. Run it
after changing any AI request setting; do not treat the live endpoint as fixed
until it succeeds.

Usage::

    python manage.py nvidia_smoke

It reads the API key from the same place the app does (Django settings, then
``NVIDIA_API_KEY``). The key is never printed.
"""

from types import SimpleNamespace

from django.core.management.base import BaseCommand

from ai.prompts import EXPLAIN_ISSUE_PROMPT, SYSTEM_INSTRUCTION
from ai.services import (
    NVIDIA_BASE_URL,
    REASONING_BUDGET_TOKENS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_OUTPUT_TOKENS,
    AIService,
    AIServiceError,
)

SAMPLE_ISSUE = SimpleNamespace(
    rule_id='image-alt',
    severity='critical',
    impact='critical',
    category='Images',
    description='Ensures <img> elements have alternate text or a role of none or presentation',
    selector='img.hero',
    help_url='https://dequeuniversity.com/rules/axe/4.10/image-alt',
    html_snippet='<img class="hero" src="/hero.png">',
)


class Command(BaseCommand):
    help = 'Send one minimal request to NVIDIA NIM to verify the live endpoint.'

    def handle(self, *args, **options):
        service = AIService()

        self.stdout.write(f'model={service.model}')
        self.stdout.write(f'base_url={NVIDIA_BASE_URL}')
        self.stdout.write(
            f'timeout={REQUEST_TIMEOUT_SECONDS}s max_tokens={MAX_OUTPUT_TOKENS} '
            f'reasoning_budget={REASONING_BUDGET_TOKENS}'
        )

        prompt = EXPLAIN_ISSUE_PROMPT.format(**service._issue_context(SAMPLE_ISSUE))
        try:
            response = service.client.chat.completions.create(
                model=service.model,
                messages=[
                    {'role': 'system', 'content': SYSTEM_INSTRUCTION},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.2,
                max_tokens=MAX_OUTPUT_TOKENS,
                response_format={'type': 'json_object'},
                **service._extra_request_params(),
            )
        except AIServiceError as exc:
            self.stderr.write(f'smoke test failed: {exc.reason}')
            raise SystemExit(1)
        except Exception as exc:  # pragma: no cover - live provider failure
            self.stderr.write(f'smoke test failed: {type(exc).__name__}: {exc}')
            raise SystemExit(1)

        finish_reason = service._finish_reason(response)
        self.stdout.write(service._empty_reply_detail(response))

        try:
            brief = service._normalize(service._reply_text(response) or '')
        except AIServiceError as exc:
            self.stderr.write(f'smoke test failed: {exc.reason}')
            raise SystemExit(1)

        if finish_reason != 'stop':
            self.stderr.write(
                'smoke test failed: response did not finish cleanly '
                f'(finish_reason={finish_reason})'
            )
            raise SystemExit(1)

        self.stdout.write('smoke test ok:')
        for field, value in brief.items():
            self.stdout.write(f'  {field}: {value[:120]}')
