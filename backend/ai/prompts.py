EXPLAIN_ISSUE_PROMPT = """You are an accessibility engineering assistant helping developers fix real accessibility issues.

Issue details:
- Rule ID: {rule_id}
- Severity: {severity}
- Impact: {impact}
- Category: {category}
- Description: {description}
- Selector: {selector}
- Help URL: {help_url}
- Affected HTML:
```html
{html_snippet}
```

Provide a clear, actionable response in the following structure:

1. Explanation (concise technical explanation)
2. Why it matters (user impact - include assistive technology users)
3. Suggested fix (high-level approach)
4. Corrected code (minimal, production-ready code snippet that fixes this specific issue)
5. Developer tip (practical guidance)

Focus on WCAG-aligned, standards-based solutions. Never invent unrelated fixes. Be specific to the provided HTML and selector.
"""

FIX_ISSUE_PROMPT = """You are an accessibility engineering assistant. Generate a practical, minimal fix for the accessibility issue below.

Issue:
- Rule ID: {rule_id}
- Severity: {severity}
- Description: {description}
- Selector: {selector}
- HTML:
```html
{html_snippet}
```

Return structured output with:
- Explanation (brief)
- Why it matters
- Suggested fix (one sentence)
- Corrected code (exact corrected HTML/markup or the minimal change needed)
- Developer tip

Prefer semantic HTML solutions. Use aria-* only when necessary. Avoid changing visual design unnecessarily. Output should be ready to copy and apply.
"""
