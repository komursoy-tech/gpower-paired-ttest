"""K2 paired t-test differential validation against statsmodels TTestPower.
Run from repository root: python differential_validation_v3.py
Does not modify core_engine.py or CLI. Deterministic 700 cases.
"""
import csv
import math
import random
from pathlib import Path

from statsmodels.stats.power import TTestPower
from scipy.stats import nct, t, norm, chi2
from scipy.integrate import quad
from core_engine import power_matched_pairs, post_hoc_matched_pairs

SEED = 20261024
TOL = 1e-6
OUT = Path('evidence') / 'differential_results.csv'
RNG = random.Random(SEED)
REF = TTestPower()


def close(a, b):
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= TOL


def reference_power(dz, n, alpha, tails):
    """statsmodels -> SciPy noncentral t -> chi-square mixture quadrature.

    The last method uses a different numerical formulation but still shares
    SciPy components with the production engine; do not call it fully independent.
    """
    value = float(REF.power(effect_size=dz, nobs=n, alpha=alpha,
                            alternative='two-sided' if tails == 2 else 'larger'))
    if math.isfinite(value):
        return value, 'statsmodels'
    df = n - 1
    delta = dz * math.sqrt(n)
    critical = float(t.isf(alpha / (2 if tails == 2 else 1), df))
    value = float(nct.sf(critical, df, delta))
    if tails == 2:
        value += float(nct.cdf(-critical, df, delta))
    if math.isfinite(value):
        return value, 'scipy-nct'

    # Integrate over V ~ chi-square(df) using normal survival probabilities.
    # This avoids the unstable noncentral-t CDF/SF route for extreme power.
    lo = max(float(chi2.ppf(1e-13, df)), 1e-300)
    hi = float(chi2.ppf(1 - 1e-13, df))
    def integrand(v):
        factor = math.sqrt(v / df)
        probability = norm.sf(critical * factor - delta)
        if tails == 2:
            probability += norm.cdf(-critical * factor - delta)
        return probability * chi2.pdf(v, df)
    value, integration_error = quad(integrand, lo, hi, epsabs=1e-11,
                                    epsrel=1e-11, limit=250)
    if not math.isfinite(value) or integration_error > 1e-7:
        raise ArithmeticError(f'Quadrature failed: {value}, err={integration_error}')
    return float(value), 'chi2-quadrature'



def record(rows, mode, index, tails, dz, alpha, n, target, actual, reference, passed, detail):
    rows.append(dict(id=index, mode=mode, tails=tails, dz=dz, alpha=alpha,
                     n_total=n, target_power=target if target is not None else '',
                     actual_power=actual if actual is not None else '',
                     reference_power=reference if reference is not None else '',
                     abs_difference=(abs(actual-reference) if actual is not None and reference is not None else ''),
                     passed=passed, detail=detail))


def main():
    rows = []
    for i in range(600):
        tails = RNG.choice((1, 2))
        dz = round(RNG.uniform(0.10, 1.5), 5)
        alpha = RNG.choice((0.001, 0.005, 0.01, 0.025, 0.05, 0.1))
        n = RNG.randint(3, 350)
        try:
            actual = post_hoc_matched_pairs(dz, n, alpha=alpha, tails=tails)['power']
            ref, source = reference_power(dz, n, alpha, tails)
            ok = close(actual, ref)
            record(rows, 'post-hoc', i+1, tails, dz, alpha, n, None, actual, ref, ok, source if ok else f'{source}: Power mismatch')
        except Exception as exc:
            record(rows, 'post-hoc', i+1, tails, dz, alpha, n, None, None, None, False, repr(exc))

    for i in range(100):
        tails = RNG.choice((1, 2))
        dz = round(RNG.uniform(0.20, 1.20), 5)
        alpha = RNG.choice((0.005, 0.01, 0.025, 0.05, 0.1))
        target = RNG.choice((0.7, 0.8, 0.85, 0.9, 0.95))
        try:
            result = power_matched_pairs(dz, alpha=alpha, target_power=target, tails=tails)
            n = result['n_total']
            actual = result['actual_power']
            ref, source = reference_power(dz, n, alpha, tails)
            prev = reference_power(dz, n-1, alpha, tails)[0] if n > 2 else None
            ok = close(actual, ref) and ref >= target - 1e-10 and (prev is None or prev < target + 1e-10)
            detail = source if ok else f'{source}: Minimality/power mismatch; previous_n_power={prev}'
            record(rows, 'a-priori', 601+i, tails, dz, alpha, n, target, actual, ref, ok, detail)
        except Exception as exc:
            record(rows, 'a-priori', 601+i, tails, dz, alpha, None, target, None, None, False, repr(exc))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    failures = [r for r in rows if not r['passed']]
    print(f'Total: {len(rows)} | PASS: {len(rows)-len(failures)} | FAIL: {len(failures)}')
    print(f'CSV: {OUT}')
    print('SciPy nct fallback cases:', sum('scipy-nct' in str(r['detail']) for r in rows))
    print('Chi-square quadrature cases:', sum('chi2-quadrature' in str(r['detail']) for r in rows))
    for r in failures[:10]:
        print('FAIL:', r)
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
