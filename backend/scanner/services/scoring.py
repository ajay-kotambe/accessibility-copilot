WEIGHTS = {
    'CRITICAL': 10,
    'SERIOUS': 7,
    'MODERATE': 4,
    'MINOR': 1,
}


def _severity_of(issue):
    """Read severity from either a plain dict or an Issue model instance."""
    if hasattr(issue, 'get'):
        return issue.get('severity') or 'MINOR'
    return getattr(issue, 'severity', None) or 'MINOR'


def calculate_score(issues):
    if not issues:
        return 100
    total = 0
    for issue in issues:
        total += WEIGHTS.get(str(_severity_of(issue)).upper(), 1)
    score = max(0, 100 - total)
    return score
