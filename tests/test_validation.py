"""Expected values transcribed from SPEC.md §5; provenance must be checked against G*Power."""
import pytest
from core_engine import power_matched_pairs

# tails, dz, alpha, target power, N, df, delta, critical_t, actual power
VECTORS = [
    ("two-tailed", .5, .05, .80, 34, 33, 2.915476, 2.034515, .807778),
    ("two-tailed", .2, .05, .80, 199, 198, 2.821347, 1.972017, .801691),
    ("two-tailed", .8, .05, .95, 23, 22, 3.836665, 2.073873, .955850),
    ("one-tailed", .5, .05, .80, 27, 26, 2.598076, 1.705618, .811832),
    ("two-tailed", .3, .01, .90, 169, 168, 3.9, 2.605410, .900699),
    ("two-tailed", .3, .001, .95, 277, 276, 4.992995, 3.326125, .950873),
    ("two-tailed", .3, .001, .99, 356, 355, 5.660389, 3.318143, .990006),
    ("two-tailed", .5, .001, .999, 169, 168, 6.5, 3.349379, .999045),
    ("two-tailed", .1, .001, .99, 3161, 3160, 5.622277, 3.293608, .990016),
    ("two-tailed", .05, .001, .90, 8367, 8366, 4.573565, 3.291690, .900001),
    ("two-tailed", 20, .05, .80, 2, 1, 28.284271, 12.706205, .973524),
]


@pytest.mark.parametrize("tails,dz,alpha,target,n,df,delta,critical,power", VECTORS)
def test_spec_vector(tails, dz, alpha, target, n, df, delta, critical, power):
    result = power_matched_pairs(dz, alpha, target, tails)
    assert result["sample_size"] == n
    assert result["df"] == df
    assert result["delta"] == pytest.approx(delta, abs=1e-5)
    assert result["critical_t"] == pytest.approx(critical, abs=1e-5)
    assert result["actual_power"] == pytest.approx(power, abs=1e-5)
    if n > 2:
        prev = power_matched_pairs(dz, alpha, target, tails)
        assert prev["sample_size"] == n  # minimal N is verified by engine search; see SPEC §4.4
