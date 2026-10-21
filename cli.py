"""Command-line interface for paired-samples t-test a-priori power analysis."""
import argparse
import json
import sys

from core_engine import (
    calculate_dz_from_differences,
    calculate_dz_from_groups,
    power_matched_pairs,
)


def build_parser():
    parser = argparse.ArgumentParser(description="G*Power-style paired-samples t-test power analysis")
    parser.add_argument("--effect-size", type=float, help="Standardized effect size dz")
    parser.add_argument("--alpha", type=float, default=0.05, help="Type I error probability (default: 0.05)")
    parser.add_argument("--power", type=float, default=0.80, help="Target power (default: 0.80)")
    parser.add_argument("--tails", choices=("one-tailed", "two-tailed"), default="two-tailed")
    parser.add_argument("--mean-diff", type=float, help="Mean of paired differences")
    parser.add_argument("--sd-diff", type=float, help="SD of paired differences")
    parser.add_argument("--mean1", type=float)
    parser.add_argument("--mean2", type=float)
    parser.add_argument("--sd1", type=float)
    parser.add_argument("--sd2", type=float)
    parser.add_argument("--correlation", type=float)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def run(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    diff_values = (args.mean_diff, args.sd_diff)
    group_values = (args.mean1, args.mean2, args.sd1, args.sd2, args.correlation)
    used = [args.effect_size is not None, any(x is not None for x in diff_values), any(x is not None for x in group_values)]
    if sum(used) != 1:
        parser.error("Choose exactly one input mode: --effect-size, --mean-diff/--sd-diff, or all five group parameters")
    if used[1] and not all(x is not None for x in diff_values):
        parser.error("Both --mean-diff and --sd-diff are required")
    if used[2] and not all(x is not None for x in group_values):
        parser.error("--mean1 --mean2 --sd1 --sd2 --correlation are all required")
    try:
        dz = (args.effect_size if used[0] else
              calculate_dz_from_differences(*diff_values) if used[1] else
              calculate_dz_from_groups(*group_values))
        result = power_matched_pairs(dz, args.alpha, args.power, args.tails)
    except (ValueError, TypeError, ZeroDivisionError, RuntimeError, OverflowError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, allow_nan=False))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
