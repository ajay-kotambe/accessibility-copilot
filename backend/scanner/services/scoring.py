WEIGHTS = {
    'CRITICAL': 10,
    'SERIOUS': 7,
    'MODERATE': 4,
    'MINOR': 1,
}


def calculate_score(issues):
    if not issues:
        return 100
    total = 0
    for issue in issues:
        sev = issue.get('severity') or issue.severity if hasattr(issue, 'severity') else 'MINOR'
        total += WEIGHTS.get(str(sev).upper(), 1)
    score = max(0, 100 - total)
    return score
