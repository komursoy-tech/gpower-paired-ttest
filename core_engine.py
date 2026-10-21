import math
import numbers
from typing import Dict, Any
import numpy as np
from scipy import integrate
from scipy.stats import t, nct, norm, chi2

MAX_SAMPLE_SIZE = 100_000


def _validate_numeric(**named_values):
    """
    SPEC.md Bölüm 6: Adım 1 ve Adım 2 kontrolleri.
    - Parametreler verilen sırayla işlenir; her parametrede sırayla:
      None -> ValueError, tür/bool -> TypeError, NaN/inf -> ValueError.
    - bool ve string gibi türler TypeError verir.
    - int, float ve numpy sayı türleri (numbers.Real) kabul edilir.
    """
    for name, val in named_values.items():
        if val is None:
            raise ValueError("Parameters cannot be NaN, Infinite or empty")

        # bool, Python'da int alt sınıfıdır; açıkça reddedilmeli
        if isinstance(val, bool) or not isinstance(val, numbers.Real):
            raise TypeError("Numeric parameters must be int or float")

        if math.isnan(val) or math.isinf(val):
            raise ValueError("Parameters cannot be NaN, Infinite or empty")


def calculate_dz_from_differences(mean_diff: float, sd_diff: float) -> float:
    """Farklar Üzerinden etki büyüklüğü hesabı."""
    _validate_numeric(mean_diff=mean_diff, sd_diff=sd_diff)

    if sd_diff < 0:
        raise ValueError("Standard deviations must be strictly positive")
    if sd_diff == 0:
        raise ZeroDivisionError("Standard deviation of difference cannot be zero")
    if mean_diff == 0:
        raise ValueError("Mean difference cannot be zero (no detectable effect)")

    dz = abs(mean_diff) / sd_diff
    if dz <= 0:
        raise ValueError("Effect size must be strictly positive")

    return float(dz)


def calculate_dz_from_groups(
    mean1: float, mean2: float, sd1: float, sd2: float, correlation: float
) -> float:
    """Grup İstatistikleri Üzerinden etki büyüklüğü hesabı."""
    _validate_numeric(
        mean1=mean1, mean2=mean2, sd1=sd1, sd2=sd2, correlation=correlation
    )

    if correlation < -1.0 or correlation > 1.0:
        raise ValueError("Correlation must be between -1 and 1")
    if sd1 <= 0 or sd2 <= 0:
        raise ValueError("Standard deviations must be strictly positive")

    scale = (sd1**2) + (sd2**2)
    radicand = scale - (2 * correlation * sd1 * sd2)

    # Göreli eşik kontrolü
    if radicand <= (1e-12 * scale):
        raise ZeroDivisionError("Standard deviation of difference cannot be zero")

    if mean1 == mean2:
        raise ValueError("Mean difference cannot be zero (no detectable effect)")

    sd_diff = math.sqrt(radicand)
    dz = abs(mean1 - mean2) / sd_diff

    if dz <= 0:
        raise ValueError("Effect size must be strictly positive")

    return float(dz)


def _nct_cdf_quad(x: float, df: int, delta: float) -> float:
    """
    Merkezi olmayan t dağılımı CDF'ini sayısal integrasyonla hesaplar:
        P(T <= x) = E_V[ Phi(x * sqrt(V/df) - delta) ],  V ~ chi2(df)
    scipy'nin nct.cdf fonksiyonu bazı (df, delta) bölgelerinde NaN döndürdüğünde
    yedek yöntem olarak kullanılır.
    """

    def integrand(v: float) -> float:
        return norm.cdf(x * math.sqrt(v / df) - delta) * chi2.pdf(v, df)

    lo = float(chi2.ppf(1e-14, df))
    if not lo > 0.0:
        lo = 1e-300
    hi = float(chi2.ppf(1.0 - 1e-14, df))
    val, _ = integrate.quad(integrand, lo, hi, epsabs=1e-13, epsrel=1e-12, limit=200)
    return min(max(float(val), 0.0), 1.0)


def _nct_cdf(x: float, df: int, delta: float) -> float:
    """
    nct.cdf; sonuç sonlu değilse (NaN) sayısal integrasyona düşer (SPEC.md Bölüm 4.5).
    errstate: scipy 1.10-1.13 sürümleri burada zararsız RuntimeWarning üretir.
    """
    with np.errstate(all="ignore"):
        value = float(nct.cdf(x, df, delta))
    if math.isfinite(value):
        return value
    return _nct_cdf_quad(x, df, delta)


def _compute_power(n: int, effect_size_dz: float, tail_prob: float, two_tailed: bool) -> tuple:
    """Belirli bir n için df, delta, t_crit ve power hesaplar."""
    df = n - 1
    delta = effect_size_dz * math.sqrt(n)
    t_crit = float(t.ppf(tail_prob, df))

    if two_tailed:
        actual_power = (1.0 - _nct_cdf(t_crit, df, delta)) + _nct_cdf(-t_crit, df, delta)
    else:
        actual_power = 1.0 - _nct_cdf(t_crit, df, delta)

    if not math.isfinite(actual_power):
        raise RuntimeError("Power computation failed")

    return df, delta, t_crit, float(actual_power)


def power_matched_pairs(
    effect_size_dz: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    tails: str = "two-tailed",
) -> Dict[str, Any]:
    """Eşleştirilmiş iki ortalama t-testi A priori güç analizi motoru."""
    _validate_numeric(
        effect_size_dz=effect_size_dz, alpha=alpha, target_power=target_power
    )

    if tails not in ["one-tailed", "two-tailed"]:
        raise ValueError("Tails must be 'one-tailed' or 'two-tailed'")
    if alpha <= 0 or alpha >= 1:
        raise ValueError("Alpha must be between 0 and 1")
    if target_power <= 0 or target_power >= 1:
        raise ValueError("Target power must be between 0 and 1")
    if effect_size_dz <= 0:
        raise ValueError("Effect size must be strictly positive")

    two_tailed = tails == "two-tailed"
    tail_prob = 1 - (alpha / 2 if two_tailed else alpha)

    # 1. Üstel arama: hedef güce ilk ulaşılan 2'nin katını bul.
    #    N_max'e ulaşılıp hâlâ yetersizse hata (spec Bölüm 4.4, adım 6).
    low = 2
    high = 2
    while True:
        _, _, _, p = _compute_power(high, effect_size_dz, tail_prob, two_tailed)
        if p >= target_power:
            break
        if high >= MAX_SAMPLE_SIZE:
            raise RuntimeError("Sample size exceeded maximum threshold")
        low = high
        high = min(high * 2, MAX_SAMPLE_SIZE)

    # 2. İkili arama: [low, high] aralığında minimal N'i bul.
    ans_n = high
    ans_metrics = None
    left = low
    right = high

    while left <= right:
        mid = (left + right) // 2
        df, delta, t_crit, cur_power = _compute_power(
            mid, effect_size_dz, tail_prob, two_tailed
        )

        if cur_power >= target_power:
            ans_n = mid
            ans_metrics = (df, delta, t_crit, cur_power)
            right = mid - 1
        else:
            left = mid + 1

    if ans_metrics is None:
        ans_metrics = _compute_power(ans_n, effect_size_dz, tail_prob, two_tailed)

    df, delta, t_crit, cur_power = ans_metrics

    return {
        "sample_size": int(ans_n),
        "df": int(df),
        "delta": float(delta),
        "critical_t": float(t_crit),
        "actual_power": float(cur_power),
    }


if __name__ == "__main__":
    # (dz, alpha, power, tails, N, df, delta, t_crit, actual_power)
    VECTORS = [
        (0.5, 0.05, 0.80, "two-tailed", 34, 33, 2.915476, 2.034515, 0.807778),
        (0.2, 0.05, 0.80, "two-tailed", 199, 198, 2.821347, 1.972017, 0.801691),
        (0.8, 0.05, 0.95, "two-tailed", 23, 22, 3.836665, 2.073873, 0.955850),
        (0.5, 0.05, 0.80, "one-tailed", 27, 26, 2.598076, 1.705618, 0.811832),
        (0.3, 0.01, 0.90, "two-tailed", 169, 168, 3.900000, 2.605410, 0.900699),
        # scipy nct.cdf'in NaN döndürdüğü bölgeler (sayısal integrasyonla doğrulandı)
        (0.3, 0.001, 0.95, "two-tailed", 277, 276, 4.992995, 3.326125, 0.950873),
        (0.3, 0.001, 0.99, "two-tailed", 356, 355, 5.660389, 3.318143, 0.990006),
        (0.5, 0.001, 0.999, "two-tailed", 169, 168, 6.500000, 3.349379, 0.999045),
        (0.1, 0.001, 0.99, "two-tailed", 3161, 3160, 5.622277, 3.293608, 0.990016),
        (0.05, 0.001, 0.90, "two-tailed", 8367, 8366, 4.573565, 3.291690, 0.900001),
    ]
    for dz, a, pw, tl, n, df, d, tc, ap in VECTORS:
        r = power_matched_pairs(dz, a, pw, tl)
        assert r["sample_size"] == n and r["df"] == df, (dz, a, pw, tl, r)
        assert abs(r["delta"] - d) <= 1e-5, (dz, a, pw, tl, r)
        assert abs(r["critical_t"] - tc) <= 1e-5, (dz, a, pw, tl, r)
        assert abs(r["actual_power"] - ap) <= 1e-5, (dz, a, pw, tl, r)

    # Çok büyük etki: N=2 yeterli (nct.cdf burada NaN döndürür)
    assert power_matched_pairs(20.0)["sample_size"] == 2

    # Determine modülü
    assert power_matched_pairs(calculate_dz_from_differences(5.0, 10.0))["sample_size"] == 34
    assert power_matched_pairs(calculate_dz_from_groups(140, 135, 10, 10, 0.5))["sample_size"] == 34
    assert power_matched_pairs(calculate_dz_from_groups(5e-7, 0, 1e-7, 1e-7, 0.5))["sample_size"] == 3

    # numpy sayı türleri kabul edilir
    assert power_matched_pairs(np.float64(0.5))["sample_size"] == 34
    assert power_matched_pairs(np.int64(1))["sample_size"] == 10

    def expect(exc, msg, fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            assert type(e) is exc and str(e) == msg, (type(e).__name__, str(e))
            return
        raise AssertionError("istisna fırlatılmadı: " + msg)

    expect(ValueError, "Parameters cannot be NaN, Infinite or empty", lambda: power_matched_pairs(None))
    # Parametre sırası: ilk geçersiz parametre hatayı belirler (SPEC.md Bölüm 6, E-15/E-16)
    expect(ValueError, "Parameters cannot be NaN, Infinite or empty", lambda: power_matched_pairs(None, "x"))
    expect(TypeError, "Numeric parameters must be int or float", lambda: power_matched_pairs("x", None))
    expect(TypeError, "Numeric parameters must be int or float", lambda: power_matched_pairs("0.5"))
    expect(ValueError, "Tails must be 'one-tailed' or 'two-tailed'", lambda: power_matched_pairs(0.5, tails="left"))
    expect(RuntimeError, "Sample size exceeded maximum threshold", lambda: power_matched_pairs(0.001))
    expect(ValueError, "Correlation must be between -1 and 1", lambda: calculate_dz_from_groups(5, 0, 10, 10, 1.5))
    expect(ZeroDivisionError, "Standard deviation of difference cannot be zero", lambda: calculate_dz_from_groups(5, 0, 10, 10, 1.0))

    print("TÜM KONTROLLER BAŞARIYLA TAMAMLANDI")