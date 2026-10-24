"""CONTRACT.md v1.0.0 strict CLI for team K2 (paired t-test)."""
import argparse
import json
import math
import sys

from core_engine import power_matched_pairs, post_hoc_matched_pairs

CONTRACT_VERSION = '1.0.0'
TEAM_NAME = 'komursoy-tech'  # Update to your official team name if different.

class CLIError(Exception):
    def __init__(self, code, field, message):
        super().__init__(message)
        self.code, self.field = code, field

class JSONParser(argparse.ArgumentParser):
    def error(self, message):
        if 'unrecognized arguments:' in message:
            raise CLIError('UNKNOWN_PARAM', 'input', message)
        if 'expected one argument' in message:
            field = message.split(':', 1)[0].lstrip('-').strip()
            raise CLIError('MISSING_PARAM', field, message)
        raise CLIError('INVALID_VALUE', 'input', message)

def parser():
    p = JSONParser(add_help=False, allow_abbrev=False)
    for field in ('test', 'mode', 'tails', 'dz', 'alpha', 'power', 'n_total'):
        p.add_argument('--' + field)
    p.add_argument('--version', action='store_true')
    return p

def number(value, field, integer=False):
    try:
        parsed = float(value)
    except (ValueError, TypeError, OverflowError):
        raise CLIError('INVALID_VALUE', field, f'{field} must be numeric')
    if not math.isfinite(parsed):
        raise CLIError('INVALID_VALUE', field, f'{field} must be finite')
    if integer and (not parsed.is_integer() or not value.lstrip('+-').isdigit()):
        raise CLIError('INVALID_VALUE', field, f'{field} must be an integer')
    return int(parsed) if integer else parsed

def execute(args):
    if args.test is None:
        raise CLIError('MISSING_PARAM', 'test', 'Missing --test')
    if args.mode is None:
        raise CLIError('MISSING_PARAM', 'mode', 'Missing --mode')
    if args.test != 't-paired':
        raise CLIError('UNSUPPORTED', 'test', f'Unsupported test: {args.test}')
    if args.mode not in ('a-priori', 'post-hoc'):
        raise CLIError('UNSUPPORTED', 'mode', f'Unsupported mode: {args.mode}')
    required = ('tails', 'dz', 'alpha', 'power' if args.mode == 'a-priori' else 'n_total')
    allowed = set(required)
    for field in ('tails', 'dz', 'alpha', 'power', 'n_total'):
        if getattr(args, field) is not None and field not in allowed:
            raise CLIError('UNKNOWN_PARAM', field, f'--{field} is not valid for {args.mode}')
    for field in required:
        if getattr(args, field) is None:
            raise CLIError('MISSING_PARAM', field, f'Missing --{field}')
    tails = number(args.tails, 'tails', integer=True)
    dz = number(args.dz, 'dz')
    alpha = number(args.alpha, 'alpha')
    if tails not in (1, 2):
        raise CLIError('OUT_OF_RANGE', 'tails', 'tails must be 1 or 2')
    if dz <= 0:
        raise CLIError('OUT_OF_RANGE', 'dz', 'dz must be > 0')
    if not 0 < alpha < 1:
        raise CLIError('OUT_OF_RANGE', 'alpha', 'alpha must be between 0 and 1')
    if args.mode == 'a-priori':
        power = number(args.power, 'power')
        if not 0 < power < 1:
            raise CLIError('OUT_OF_RANGE', 'power', 'power must be between 0 and 1')
        if power <= alpha:
            raise CLIError('INCONSISTENT', 'power', 'power must exceed alpha')
        result = power_matched_pairs(dz, alpha=alpha, target_power=power, tails=tails)
        keys = ('ncp', 'critical_t', 'df', 'n_total', 'actual_power')
    else:
        n_total = number(args.n_total, 'n_total', integer=True)
        if n_total < 2:
            raise CLIError('OUT_OF_RANGE', 'n_total', 'n_total must be >= 2')
        result = post_hoc_matched_pairs(dz, n_total, alpha=alpha, tails=tails)
        keys = ('ncp', 'critical_t', 'df', 'power')
    return {k: (int(result[k]) if k == 'df' or k == 'n_total' else float(result[k])) for k in keys}

def run(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.version:
            if any(getattr(args, k) is not None for k in ('test','mode','tails','dz','alpha','power','n_total')):
                raise CLIError('UNKNOWN_PARAM', 'version', '--version cannot be combined with analysis arguments')
            result = {'contract_version': CONTRACT_VERSION, 'name': TEAM_NAME,
                      'engine': f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'}
        else:
            result = execute(args)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')))
        return 0
    except CLIError as exc:
        print(json.dumps({'error': str(exc), 'code': exc.code, 'field': exc.field}, ensure_ascii=False))
        return 2
    except (ValueError, TypeError, ArithmeticError, RuntimeError) as exc:
        msg = str(exc)
        if 'maximum' in msg.lower() or 'no solution' in msg.lower():
            print(json.dumps({'error': msg, 'code': 'NO_SOLUTION', 'field': 'n_total'}))
            return 2
        print(json.dumps({'error': msg, 'code': 'INTERNAL', 'field': 'input'}))
        return 1

if __name__ == '__main__':
    sys.exit(run())

def main():
    sys.exit(run())
