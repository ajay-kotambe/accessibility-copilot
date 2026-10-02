import os
from openai import OpenAI
from django.conf import settings

from .prompts import EXPLAIN_ISSUE_PROMPT, FIX_ISSUE_PROMPT


class AIService:
    def __init__(self):
        api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

    def _parse_response(self, content):
        result = {
            'explanation': '',
            'why_it_matters': '',
            'suggested_fix': '',
            'corrected_code': '',
            'developer_tip': '',
        }
        if not content:
            return result
        # Simple section parsing; fallback to full content
        sections = {
            '1. explanation': 'explanation',
            'explanation': 'explanation',
            '2. why it matters': 'why_it_matters',
            'why it matters': 'why_it_matters',
            '3. suggested fix': 'suggested_fix',
            'suggested fix': 'suggested_fix',
            '4. corrected code': 'corrected_code',
            'corrected code': 'corrected_code',
            '5. developer tip': 'developer_tip',
            'developer tip': 'developer_tip',
        }
        current = None
        lines = content.splitlines()
        for line in lines:
            lowered = line.strip().lower()
            matched = False
            for key, field in sections.items():
                if key in lowered:
                    current = field
                    matched = True
                    break
            if matched:
                continue
            if current:
                result[current] += line + '\n'
        # If no sections parsed, use whole as explanation
        if not any(result.values()):
            result['explanation'] = content
        # Clean up code fences
        for key in ['corrected_code']:
            val = result.get(key, '')
            if '```' in val:
                parts = val.split('```')
                if len(parts) >= 3:
                    result[key] = parts[1].strip()
                else:
                    result[key] = val.replace('```', '').strip()
        return {k: v.strip() for k, v in result.items()}

    def analyze_issue(self, issue):
        if not self.client:
            return {
                'explanation': issue.description,
                'why_it_matters': 'This issue can impact users who rely on assistive technologies.',
                'suggested_fix': 'Address the issue according to accessibility best practices.',
                'corrected_code': issue.html_snippet or '',
                'developer_tip': 'Test with keyboard and screen reader after applying fix.',
            }
        context = {
            'rule_id': issue.rule_id,
            'severity': issue.severity,
            'impact': issue.impact or '',
            'category': issue.category or '',
            'description': issue.description,
            'selector': issue.selector or '',
            'help_url': issue.help_url or '',
            'html_snippet': issue.html_snippet or '',
        }
        prompt = EXPLAIN_ISSUE_PROMPT.format(**context)
        try:
            resp = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
        except Exception:
            content = ''
        return self._parse_response(content)

    def generate_fix(self, issue):
        if not self.client:
            return self.analyze_issue(issue)
        context = {
            'rule_id': issue.rule_id,
            'severity': issue.severity,
            'description': issue.description,
            'selector': issue.selector or '',
            'html_snippet': issue.html_snippet or '',
        }
        prompt = FIX_ISSUE_PROMPT.format(**context)
        try:
            resp = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.1,
            )
            content = resp.choices[0].message.content
        except Exception:
            content = ''
        return self._parse_response(content)
