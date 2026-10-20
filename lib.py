from datetime import datetime


def zip5(z):
    return z[:5] if z else None


def unit_bucket(n):
    if n is None: return "unknown"     
    if n == 0:    return "zero"        
    if n == 1:    return "1"
    if n <= 4:    return "2-4"
    if n <= 19:   return "5-19"
    return "20+"


def days_between(iso_a, iso_b):
    if not iso_a or not iso_b:
        return None
    a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
    b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    return (b - a).days


def trailing_window(issue_year, n=2):
    if issue_year is None:
        return []
    y = int(issue_year)
    return [str(y - k) for k in range(n, 0, -1)]


def approx_gfa_per_unit(area, stories, units):
    if not units or area is None or stories is None:
        return None
    return area * stories / units


def carry_cost(land, hard, build_days, sell_days, rate, hold_days=0):
    land_period = hold_days + build_days + sell_days
    return rate * (
        land * land_period / 365.0
        + hard * 0.5 * build_days / 365.0
        + hard * 1.0 * sell_days / 365.0
    )


def max_build_budget(price, land, build_days, sell_days, rate, hurdle,
                     hold_days=0):
    total = hold_days + build_days + sell_days
    if total <= 0:
        return None
    basis  = price / (1 + hurdle * total / 365.0)
    land_f = 1 + rate * total / 365.0
    hard_f = 1 + rate * (0.5 * build_days + sell_days) / 365.0
    return (basis - land * land_f) / hard_f