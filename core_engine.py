"""
G*Power 3.1.9.7 uyumlu eşleştirilmiş iki ortalama t-testi (t-paired) güç analizi motoru.

Kapsam: a-priori (örneklem büyüklüğü), post-hoc (ulaşılan güç) ve Determine (d_z türetme).
Referans: SPEC.md (Bölüm 4: matematik, Bölüm 5: vektörler, Bölüm 6: hata hiyerarşisi).
"""
import math
import numbers
import warnings
from typing import Any, Dict, Union

import numpy as np
from scipy import integrate
from scipy.stats import chi2, nct, norm, t

MAX_SAMPLE_SIZE = 100_000


# ---------------------------------------------------------------------------
# Girdi doğrulama (SPEC.md Bölüm 6, Adım 1-2)
# ---------------------------------------------------------------------------
def _validate_numeric(**named_values):
    """
    Parametreler verilen (imza) sırasıyla denetlenir; her parametrede sırayla:
      None -> ValueError, bool/tür -> TypeError, NaN/inf -> ValueError.
    """
    for _name, val in named_values.items():
        if val is None:
            raise ValueError("Parameters cannot be NaN, Infinite or empty")

        if isinstance(val, (bool, np.bool_)) or not isinstance(val, numbers.Real):
            raise TypeError("Numeric parameters must be int or float")

        try:
            if math.isnan(val) or math.isinf(val):
                raise ValueError("Parameters cannot be NaN, Infinite or empty")
        except OverflowError:
            # Float'a çevrilemeyecek kadar büyük tam sayılar
            raise ValueError("Parameters cannot be NaN, Infinite or empty")


def _validate_tails(tails: Any) -> bool:
    """
    Yalnızca 'one-tailed', 'two-tailed' (str) ile 1, 2 (int / numpy tam sayı) kabul edilir.
    bool, None, "1", "2", 1.0, 2.0 ve diğer her şey reddedilir.
    Dönüş: True -> çift yönlü, False -> tek yönlü.
    """
    if isinstance(tails, str):
        if tails == "two-tailed":
            return True
        if tails == "one-tailed":
            return False
    elif isinstance(tails, (int, np.integer)) and not isinstance(tails, (bool, np.bool_)):
        if tails == 2:
            return True
        if tails == 1:
            return False
    raise ValueError("Tails must be 'one-tailed' or 'two-tailed'")


# ---------------------------------------------------------------------------
# Determine modülü
# ---------------------------------------------------------------------------
def calculate_dz_from_differences(mean_diff: float, sd_diff: float) -> float:
    """Farklar üzerinden etki büyüklüğü: d_z = |mu_D| / sigma_D."""
    _validate_numeric(mean_diff=mean_diff, sd_diff=sd_diff)

    if sd_diff < 0:
        raise ValueError("Standard deviations must be strictly positive")
    if sd_diff == 0:
        raise ZeroDivisionError("Standard deviation of difference cannot be zero")
    if mean_diff == 0:
        raise ValueError("Mean difference cannot be zero (no detectable effect)")

    return float(abs(mean_diff) / sd_diff)


def calculate_dz_from_groups(
    mean1: float, mean2: float, sd1: float, sd2: float, correlation: float
) -> float:
    """Grup istatistikleri üzerinden etki büyüklüğü (göreli sıfır eşiğiyle)."""
    _validate_numeric(
        mean1=mean1, mean2=mean2, sd1=sd1, sd2=sd2, correlation=correlation
    )

    if correlation < -1.0 or correlation > 1.0:
        raise ValueError("Correlation must be between -1 and 1")
    if sd1 <= 0 or sd2 <= 0:
        raise ValueError("Standard deviations must be strictly positive")

    scale = (sd1**2) + (sd2**2)
    radicand = scale - (2 * correlation * sd1 * sd2)

    # Göreli eşik: birimden bağımsız (SPEC.md Bölüm 2.2)
    if radicand <= (1e-12 * scale):
        raise ZeroDivisionError("Standard deviation of difference cannot be zero")

    if mean1 == mean2:
        raise ValueError("Mean difference cannot be zero (no detectable effect)")

    return float(abs(mean1 - mean2) / math.sqrt(radicand))


# ---------------------------------------------------------------------------
# Merkezi olmayan t CDF'i ve güç hesabı (SPEC.md Bölüm 4)
# ---------------------------------------------------------------------------
def _nct_cdf_quad(x: float, df: int, delta: float) -> float:
    """
    Merkezi olmayan t CDF'ini ki-kare integrasyonuyla hesaplar:
        P(T <= x) = E_V[ Phi(x * sqrt(V/df) - delta) ],  V ~ chi2(df)
    """

    def integrand(v: float) -> float:
        return norm.cdf(x * math.sqrt(v / df) - delta) * chi2.pdf(v, df)

    lo = float(chi2.ppf(1e-14, df))
    if not lo > 0.0:
        lo = 1e-300
    hi = float(chi2.ppf(1.0 - 1e-14, df))
    with warnings.catch_warnings():
        # Mutlak hata 1e-13 civarında kaldığından yuvarlama uyarıları zararsızdır.
        warnings.simplefilter("ignore", integrate.IntegrationWarning)
        val, _ = integrate.quad(
            integrand, lo, hi, epsabs=1e-13, epsrel=1e-12, limit=200
        )
    return min(max(float(val), 0.0), 1.0)


def _nct_cdf(x: float, df: int, delta: float) -> float:
    """nct.cdf; sonuç sonlu değilse (NaN) sayısal integrasyona düşer (SPEC.md Bölüm 4.5)."""
    with np.errstate(all="ignore"):
        value = float(nct.cdf(x, df, delta))
    if math.isfinite(value):
        return value
    return _nct_cdf_quad(x, df, delta)


def _compute_power(n: int, effect_size_dz: float, alpha_tail: float, two_tailed: bool) -> tuple:
    """
    Belirli bir n için (df, delta, t_crit, power) hesaplar.
    alpha_tail: kuyruk başına olasılık (çift yönlü: alpha/2, tek yönlü: alpha).
    t_crit için t.isf kullanılır; t.ppf(1 - alpha_tail) küçük alpha'da hassasiyet kaybeder.
    """
    df = n - 1
    delta = effect_size_dz * math.sqrt(n)
    t_crit = float(t.isf(alpha_tail, df))

    if not math.isfinite(t_crit):
        raise RuntimeError("Power computation failed")

    if two_tailed:
        actual_power = (1.0 - _nct_cdf(t_crit, df, delta)) + _nct_cdf(-t_crit, df, delta)
    else:
        actual_power = 1.0 - _nct_cdf(t_crit, df, delta)

    if not math.isfinite(actual_power):
        raise RuntimeError("Power computation failed")

    return df, delta, t_crit, float(actual_power)


# ---------------------------------------------------------------------------
# Genel analiz fonksiyonları
# ---------------------------------------------------------------------------
def power_matched_pairs(
    effect_size_dz: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    tails: Union[str, int] = "two-tailed",
) -> Dict[str, Any]:
    """A-priori: hedef güce ulaşan minimal toplam çift sayısı N."""
    _validate_numeric(effect_size_dz=effect_size_dz, alpha=alpha, target_power=target_power)
    two_tailed = _validate_tails(tails)

    if alpha <= 0 or alpha >= 1:
        raise ValueError("Alpha must be between 0 and 1")
    if target_power <= 0 or target_power >= 1:
        raise ValueError("Target power must be between 0 and 1")
    if effect_size_dz <= 0:
        raise ValueError("Effect size must be strictly positive")

    alpha_tail = alpha / 2 if two_tailed else alpha

    # 1. Üstel arama: hedef güce ilk ulaşılan üst sınırı bul.
    low = 2
    high = 2
    while True:
        _, _, _, p = _compute_power(high, effect_size_dz, alpha_tail, two_tailed)
        if p >= target_power:
            break
        if high >= MAX_SAMPLE_SIZE:
            raise RuntimeError("Sample size exceeded maximum threshold")
        low = high
        high = min(high * 2, MAX_SAMPLE_SIZE)

    # 2. İkili arama: [low, high] aralığında minimal N.
    ans_n = high
    ans_metrics = None
    left, right = low, high
    while left <= right:
        mid = (left + right) // 2
        df, delta, t_crit, cur_power = _compute_power(mid, effect_size_dz, alpha_tail, two_tailed)
        if cur_power >= target_power:
            ans_n = mid
            ans_metrics = (df, delta, t_crit, cur_power)
            right = mid - 1
        else:
            left = mid + 1

    if ans_metrics is None:
        ans_metrics = _compute_power(ans_n, effect_size_dz, alpha_tail, two_tailed)

    df, delta, t_crit, cur_power = ans_metrics

    # Çıktı şeması: SPEC.md Bölüm 3.1 (fazladan anahtar yok)
    return {
        "ncp": float(delta),
        "critical_t": float(t_crit),
        "df": int(df),
        "n_total": int(ans_n),
        "actual_power": float(cur_power),
    }


def post_hoc_matched_pairs(
    effect_size_dz: float,
    n_total: int,
    alpha: float = 0.05,
    tails: Union[str, int] = "two-tailed",
) -> Dict[str, Any]:
    """Post-hoc: verilen N, d_z ve alpha için ulaşılan güç."""
    _validate_numeric(effect_size_dz=effect_size_dz, n_total=n_total, alpha=alpha)
    two_tailed = _validate_tails(tails)

    # Tür fark etmeksizin (float, numpy, Fraction) tam sayı değerli olmalı.
    if n_total != math.floor(n_total):
        raise TypeError("Sample size must be an integer")

    if n_total < 2:
        raise ValueError("Sample size (n_total) must be >= 2")
    if n_total > MAX_SAMPLE_SIZE:
        raise RuntimeError("Sample size exceeded maximum threshold")

    if alpha <= 0 or alpha >= 1:
        raise ValueError("Alpha must be between 0 and 1")
    if effect_size_dz <= 0:
        raise ValueError("Effect size must be strictly positive")

    n_val = int(n_total)
    alpha_tail = alpha / 2 if two_tailed else alpha
    df, delta, t_crit, calculated_power = _compute_power(n_val, effect_size_dz, alpha_tail, two_tailed)

    # Çıktı şeması: SPEC.md Bölüm 3.2 (fazladan anahtar yok)
    return {
        "ncp": float(delta),
        "critical_t": float(t_crit),
        "df": int(df),
        "power": float(calculated_power),
        "n_total": int(n_val),
    }


# ---------------------------------------------------------------------------
# Kendi kendine test (python core_engine.py)
# ---------------------------------------------------------------------------
def _reference_linear_n(effect_size_dz, alpha, target_power, two_tailed):
    """SPEC.md Bölüm 4.4.A referans doğrusal algoritması (yalnızca test amaçlı)."""
    alpha_tail = alpha / 2 if two_tailed else alpha
    for n in range(2, MAX_SAMPLE_SIZE + 1):
        if _compute_power(n, effect_size_dz, alpha_tail, two_tailed)[3] >= target_power:
            return n
    raise RuntimeError("Sample size exceeded maximum threshold")


def _self_test():
    # (dz, alpha, target_power, tails, N, df, delta, t_crit, actual_power)  -- SPEC.md V-01..V-21, V-33, V-34
    A_PRIORI_VECTORS = [
        (0.5, 0.05, 0.80, 2, 34, 33, 2.915476, 2.034515, 0.807778),
        (0.2, 0.05, 0.80, 2, 199, 198, 2.821347, 1.972017, 0.801691),
        (0.8, 0.05, 0.80, 2, 15, 14, 3.098387, 2.144787, 0.821311),
        (0.5, 0.05, 0.90, 2, 44, 43, 3.316625, 2.016692, 0.900031),
        (0.5, 0.05, 0.95, 2, 54, 53, 3.674235, 2.005746, 0.950212),
        (0.8, 0.05, 0.95, 2, 23, 22, 3.836665, 2.073873, 0.955850),
        (0.3, 0.01, 0.90, 2, 169, 168, 3.900000, 2.605410, 0.900699),
        (0.4, 0.01, 0.95, 2, 115, 114, 4.289522, 2.619645, 0.950622),
        (0.5, 0.05, 0.80, 1, 27, 26, 2.598076, 1.705618, 0.811832),
        (0.2, 0.05, 0.80, 1, 156, 155, 2.497999, 1.654744, 0.800167),
        (0.8, 0.05, 0.80, 1, 12, 11, 2.771281, 1.795885, 0.828981),
        (0.5, 0.01, 0.90, 1, 55, 54, 3.708099, 2.397410, 0.901121),
        (0.5, 0.05, 0.95, 1, 45, 44, 3.354102, 1.680230, 0.951240),
        (0.3, 0.05, 0.90, 1, 97, 96, 2.954657, 1.660881, 0.901280),
        (0.4, 0.01, 0.80, 1, 66, 65, 3.249615, 2.385097, 0.803798),
        (0.3, 0.001, 0.95, 2, 277, 276, 4.992995, 3.326125, 0.950873),
        (0.3, 0.001, 0.99, 2, 356, 355, 5.660389, 3.318143, 0.990006),
        (0.5, 0.001, 0.999, 2, 169, 168, 6.500000, 3.349379, 0.999045),
        (0.1, 0.001, 0.99, 2, 3161, 3160, 5.622277, 3.293608, 0.990016),
        (0.05, 0.001, 0.90, 2, 8367, 8366, 4.573565, 3.291690, 0.900001),
        (20.0, 0.05, 0.80, 2, 2, 1, 28.284271, 12.706205, 0.973524),
        (0.5, 1e-10, 0.90, 2, 261, 260, 8.077747, 6.742856, 0.900823),
        (1.0, 1e-15, 0.90, 2, 117, 116, 10.816654, 9.306772, 0.904018),
    ]
    TAIL_NAMES = {1: "one-tailed", 2: "two-tailed"}

    for dz, a, pw, tl, n, df, d, tc, ap in A_PRIORI_VECTORS:
        for tails_arg in (tl, TAIL_NAMES[tl]):
            r = power_matched_pairs(dz, a, pw, tails_arg)
            assert set(r) == {"ncp", "critical_t", "df", "n_total", "actual_power"}, r
            assert r["n_total"] == n and r["df"] == df, ("A-priori N/df", dz, a, pw, tl, r)
            assert abs(r["ncp"] - d) <= 1e-5, ("A-priori ncp", r)
            assert abs(r["critical_t"] - tc) <= 1e-5, ("A-priori t_crit", r)
            assert abs(r["actual_power"] - ap) <= 1e-5, ("A-priori power", r)
        # Bağımsız çapraz kontrol: nct.cdf'ten bağımsız integrasyonla güç
        _, _, tcq, _ = _compute_power(n, dz, a / 2 if tl == 2 else a, tl == 2)
        pq = 1 - _nct_cdf_quad(tcq, df, dz * math.sqrt(n))
        if tl == 2:
            pq += _nct_cdf_quad(-tcq, df, dz * math.sqrt(n))
        assert abs(pq - r["actual_power"]) <= 1e-6, ("quad çapraz kontrol", dz, a, pw, tl, pq, r)

    # (dz, n_total, alpha, tails, power, t_crit, ncp)  -- SPEC.md V-22..V-32
    POST_HOC_VECTORS = [
        (0.50, 45, 0.05, 1, 0.951240, 1.680230, 3.354102),
        (0.35, 40, 0.05, 2, 0.578855, 2.022691, 2.213594),
        (0.25, 80, 0.05, 2, 0.598282, 1.990450, 2.236068),
        (0.60, 25, 0.01, 2, 0.585717, 2.796940, 3.000000),
        (0.15, 200, 0.05, 1, 0.680553, 1.652547, 2.121320),
        (0.45, 60, 0.05, 2, 0.929008, 2.000995, 3.485685),
        (0.40, 50, 0.05, 2, 0.791787, 2.009575, 2.828427),
        (0.60, 20, 0.01, 2, 0.450116, 2.860935, 2.683282),
        (0.20, 50, 0.05, 1, 0.401222, 1.676551, 1.414214),
        (0.70, 30, 0.05, 2, 0.959446, 2.045230, 3.834058),
        (1.00, 10, 0.05, 2, 0.803097, 2.262157, 3.162278),
    ]
    for dz, n, a, tl, ep, etc, encp in POST_HOC_VECTORS:
        for tails_arg in (tl, TAIL_NAMES[tl]):
            pr = post_hoc_matched_pairs(dz, n, a, tails_arg)
            assert set(pr) == {"ncp", "critical_t", "df", "power", "n_total"}, pr
            assert pr["df"] == n - 1 and pr["n_total"] == n, pr
            assert abs(pr["power"] - ep) <= 1e-5, ("Post-hoc power", dz, n, a, tl, pr)
            assert abs(pr["critical_t"] - etc) <= 1e-5, ("Post-hoc t_crit", pr)
            assert abs(pr["ncp"] - encp) <= 1e-5, ("Post-hoc ncp", pr)

    # Determine vektörleri (V-DET-01..03)
    assert power_matched_pairs(calculate_dz_from_differences(5.0, 10.0))["n_total"] == 34
    assert power_matched_pairs(calculate_dz_from_groups(140, 135, 10, 10, 0.5))["n_total"] == 34
    r3 = power_matched_pairs(calculate_dz_from_groups(5e-7, 0, 1e-7, 1e-7, 0.5))
    assert r3["n_total"] == 3 and r3["df"] == 2
    assert abs(r3["ncp"] - 8.660254) <= 1e-5 and abs(r3["critical_t"] - 4.302653) <= 1e-5
    assert abs(r3["actual_power"] - 0.975462) <= 1e-5

    # Kabul edilen sayısal türler
    assert power_matched_pairs(np.float64(0.5))["n_total"] == 34
    assert power_matched_pairs(np.int64(1))["n_total"] == 10
    assert power_matched_pairs(0.5, tails=np.int64(2))["n_total"] == 34
    ref = post_hoc_matched_pairs(0.5, 34)["power"]
    for n_arg in (34.0, np.int64(34), np.float64(34.0), __import__("fractions").Fraction(68, 2)):
        assert post_hoc_matched_pairs(0.5, n_arg)["power"] == ref and post_hoc_matched_pairs(0.5, n_arg)["n_total"] == 34

    # Küçük alpha: t_crit, isf ile tam hesaplanmalı (ppf(1 - alpha/2) burada bozulur)
    r = power_matched_pairs(1.0, alpha=1e-17, target_power=0.90)
    assert abs(r["critical_t"] - float(t.isf(0.5e-17, r["df"]))) <= 1e-9 and math.isfinite(r["critical_t"])

    # Monotonluk (zayıf, NaN yedek yolu dahil) ve doğrusal referansla eşitlik
    for dz, a, two in [(0.5, 0.05, True), (0.2, 0.001, True), (0.3, 0.01, False)]:
        at = a / 2 if two else a
        prev = -1.0
        for n in range(2, 601):
            p = _compute_power(n, dz, at, two)[3]
            assert math.isfinite(p) and p >= prev - 1e-9, ("Monotonluk bozuldu", dz, a, two, n, prev, p)
            prev = p
    for dz, a, pw, two in [(0.5, 0.05, 0.80, True), (0.3, 0.001, 0.99, True), (0.2, 0.05, 0.80, False),
                           (0.4, 0.01, 0.95, True), (0.8, 0.001, 0.999, False), (0.5, 1e-10, 0.90, True)]:
        fast = power_matched_pairs(dz, a, pw, "two-tailed" if two else "one-tailed")["n_total"]
        assert fast == _reference_linear_n(dz, a, pw, two), ("Doğrusal != ikili", dz, a, pw, two, fast)

    # Negatif vektörler (SPEC.md E-01 .. E-29): tür ve mesaj birebir
    def expect(exc, msg, fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            assert type(e) is exc and str(e) == msg, (type(e).__name__, str(e), "beklenen:", exc.__name__, msg)
            return
        raise AssertionError("istisna fırlatılmadı: " + msg)

    NAN_MSG = "Parameters cannot be NaN, Infinite or empty"
    TYPE_MSG = "Numeric parameters must be int or float"
    TAILS_MSG = "Tails must be 'one-tailed' or 'two-tailed'"
    SD_MSG = "Standard deviations must be strictly positive"
    ZERO_MSG = "Standard deviation of difference cannot be zero"
    MEAN_MSG = "Mean difference cannot be zero (no detectable effect)"
    N_MSG = "Sample size (n_total) must be >= 2"
    INT_MSG = "Sample size must be an integer"
    MAXN_MSG = "Sample size exceeded maximum threshold"
    Frac = __import__("fractions").Fraction

    expect(ValueError, TAILS_MSG, lambda: power_matched_pairs(0.5, tails="left"))                          # E-01
    expect(ValueError, "Effect size must be strictly positive", lambda: power_matched_pairs(0))            # E-02
    expect(ValueError, "Effect size must be strictly positive", lambda: power_matched_pairs(-0.5))         # E-03
    expect(ValueError, "Alpha must be between 0 and 1", lambda: power_matched_pairs(0.5, alpha=1.0))      # E-04
    expect(ValueError, "Target power must be between 0 and 1", lambda: power_matched_pairs(0.5, target_power=0))  # E-05
    expect(ValueError, NAN_MSG, lambda: power_matched_pairs(float("nan")))                                 # E-06
    expect(TypeError, TYPE_MSG, lambda: power_matched_pairs("0.5"))                                        # E-07
    expect(RuntimeError, MAXN_MSG, lambda: power_matched_pairs(0.001))                                     # E-08
    expect(ValueError, MEAN_MSG, lambda: calculate_dz_from_differences(0, 10))                             # E-09
    expect(ZeroDivisionError, ZERO_MSG, lambda: calculate_dz_from_differences(5, 0))                       # E-10
    expect(ValueError, SD_MSG, lambda: calculate_dz_from_differences(5, -1))                               # E-11
    expect(ZeroDivisionError, ZERO_MSG, lambda: calculate_dz_from_groups(5, 0, 10, 10, 1.0))               # E-12
    expect(ValueError, "Correlation must be between -1 and 1", lambda: calculate_dz_from_groups(5, 0, 10, 10, 1.5))  # E-13
    expect(ValueError, SD_MSG, lambda: calculate_dz_from_groups(5, 0, 0, 10, 0.5))                         # E-14
    expect(ValueError, NAN_MSG, lambda: power_matched_pairs(None, "x"))                                    # E-15
    expect(TypeError, TYPE_MSG, lambda: power_matched_pairs("x", None))                                    # E-16
    expect(ValueError, N_MSG, lambda: post_hoc_matched_pairs(0.5, 1))                                      # E-17
    expect(TypeError, TYPE_MSG, lambda: power_matched_pairs(True))                                         # E-18
    expect(ValueError, NAN_MSG, lambda: power_matched_pairs(float("inf")))                                 # E-19
    expect(ValueError, TAILS_MSG, lambda: power_matched_pairs(0.5, tails=None))                            # E-20
    expect(ValueError, TAILS_MSG, lambda: power_matched_pairs(0.5, tails=True))                            # E-21
    expect(ValueError, TAILS_MSG, lambda: power_matched_pairs(0.5, tails="1"))                             # E-22
    expect(ValueError, TAILS_MSG, lambda: power_matched_pairs(0.5, tails=1.0))                             # E-23
    expect(TypeError, INT_MSG, lambda: post_hoc_matched_pairs(0.5, 34.5))                                  # E-24
    expect(TypeError, INT_MSG, lambda: post_hoc_matched_pairs(0.5, Frac(69, 2)))                           # E-25
    expect(RuntimeError, MAXN_MSG, lambda: post_hoc_matched_pairs(0.5, MAX_SAMPLE_SIZE + 1))               # E-26
    expect(ValueError, N_MSG, lambda: post_hoc_matched_pairs(0.0, 1))                                      # E-27 (sıra: N < 2, d_z <= 0'dan önce)
    expect(TypeError, TYPE_MSG, lambda: post_hoc_matched_pairs(0.5, "34"))                                 # E-28
    expect(ValueError, NAN_MSG, lambda: post_hoc_matched_pairs(0.5, None))                                 # E-29

    print("TÜM KONTROLLER BAŞARIYLA TAMAMLANDI (23 a-priori + 11 post-hoc + 3 Determine vektörü, 29 negatif senaryo)")


if __name__ == "__main__":
    _self_test()