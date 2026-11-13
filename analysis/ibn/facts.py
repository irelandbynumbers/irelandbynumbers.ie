"""Small helpers for writing a chart's key fact from its data, so the sentence
always matches the latest figures."""


def pct_change(new, old, digits=0):
    """'up 12%' or 'down 3%' (or 'unchanged'), comparing new with old."""
    p = (new / old - 1) * 100
    if round(p, digits) == 0:
        return "unchanged"
    return f"{'up' if p > 0 else 'down'} {abs(p):.{digits}f}%"


def higher_lower(p, digits=1):
    """'3.2% higher' or '0.4% lower' for a percentage difference."""
    if round(p, digits) == 0:
        return "unchanged"
    return f"{abs(p):.{digits}f}% {'higher' if p > 0 else 'lower'}"


def millions(n, digits=2):
    return f"{n / 1e6:.{digits}f} million"


def lower_first(s):
    return s[:1].lower() + s[1:]
