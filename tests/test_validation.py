"""SPEC.md reference numbers; independent G*Power GUI verification remains separate."""
import pytest
from core_engine import power_matched_pairs, post_hoc_matched_pairs

# (tails, dz, alpha, target power, N, df, ncp, critical_t, actual power)
A_PRIORI = [
    (2, .5, .05, .8, 34, 33, 2.915476, 2.034515, .807778),
    (2, .2, .05, .8, 199, 198, 2.821347, 1.972017, .801691),
    (2, .8, .05, .95, 23, 22, 3.836665, 2.073873, .955850),
    (1, .5, .05, .8, 27, 26, 2.598076, 1.705618, .811832),
    (2, .3, .01, .9, 169, 168, 3.9, 2.605410, .900699),
    (2, .3, .001, .95, 277, 276, 4.992995, 3.326125, .950873),
    (2, .3, .001, .99, 356, 355, 5.660389, 3.318143, .990006),
    (2, .5, .001, .999, 169, 168, 6.5, 3.349379, .999045),
    (2, .1, .001, .99, 3161, 3160, 5.622277, 3.293608, .990016),
    (2, .05, .001, .9, 8367, 8366, 4.573565, 3.291690, .900001),
    (2, 20, .05, .8, 2, 1, 28.284271, 12.706205, .973524),
]


@pytest.mark.parametrize("tails,dz,alpha,target,n,df,ncp,critical,power", A_PRIORI)
def test_apriori_vector(tails, dz, alpha, target, n, df, ncp, critical, power):
    result = power_matched_pairs(dz, alpha, target, tails)
    assert result["n_total"] == n
    assert result["df"] == df
    assert result["ncp"] == pytest.approx(ncp, abs=1e-5, rel=0)
    assert result["critical_t"] == pytest.approx(critical, abs=1e-5, rel=0)
    assert result["actual_power"] == pytest.approx(power, abs=1e-5, rel=0)


@pytest.mark.parametrize("tails,dz,n,alpha,expected_power", [
    (2, .5, 34, .05, .807778),
    (1, .5, 45, .05, .951240),
    (2, .35, 40, .05, .578855),
    (2, 1., 10, .05, .803097),
])
def test_posthoc_vector(tails, dz, n, alpha, expected_power):
    result = post_hoc_matched_pairs(dz, n, alpha, tails)
    assert result["n_total"] == n
    assert result["df"] == n - 1
    assert result["power"] == pytest.approx(expected_power, abs=1e-5, rel=0)
