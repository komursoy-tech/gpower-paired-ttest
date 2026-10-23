"""Existing core validation checks updated for the new output schema."""
import re
import pytest
from core_engine import calculate_dz_from_differences, calculate_dz_from_groups, power_matched_pairs, post_hoc_matched_pairs


def test_determine_differences():
    assert calculate_dz_from_differences(5, 10) == .5
    assert power_matched_pairs(.5)["n_total"] == 34


def test_determine_groups():
    assert calculate_dz_from_groups(140, 135, 10, 10, .5) == .5


def test_post_hoc():
    result = post_hoc_matched_pairs(.5, 34)
    assert result["n_total"] == 34
    assert result["df"] == 33
    assert result["power"] == pytest.approx(.8077775, abs=1e-5)


@pytest.mark.parametrize("kwargs,exception,message", [
    ({"effect_size_dz": 0}, ValueError, "Effect size must be strictly positive"),
    ({"effect_size_dz": "0.5"}, TypeError, "Numeric parameters must be int or float"),
    ({"effect_size_dz": None}, ValueError, "Parameters cannot be NaN, Infinite or empty"),
    ({"effect_size_dz": .5, "tails": "left"}, ValueError, "Tails must be 'one-tailed' or 'two-tailed'"),
    ({"effect_size_dz": .5, "alpha": 1}, ValueError, "Alpha must be between 0 and 1"),
    ({"effect_size_dz": .5, "target_power": 0}, ValueError, "Target power must be between 0 and 1"),
])
def test_invalid_parameters(kwargs, exception, message):
    with pytest.raises(exception, match="^" + re.escape(message) + "$"):
        power_matched_pairs(**kwargs)


def test_zero_standard_deviation():
    with pytest.raises(ZeroDivisionError):
        calculate_dz_from_differences(5, 0)
