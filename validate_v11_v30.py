"""Batch-run the paired t-test CLI for G*Power screenshots V-11..V-30.
Does not infer screenshot values or claim a pass without a GUI comparison.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

CASES = [
    ('V-11','a-priori',2,0.2,0.01,0.90),
    ('V-12','a-priori',1,0.3,0.05,0.80),
    ('V-13','a-priori',2,0.5,0.01,0.80),
    ('V-14','a-priori',1,0.4,0.01,0.90),
    ('V-15','a-priori',2,0.6,0.05,0.95),
    ('V-16','a-priori',1,0.7,0.05,0.80),
    ('V-17','a-priori',2,0.9,0.05,0.90),
    ('V-18','a-priori',1,0.2,0.01,0.95),
    ('V-19','a-priori',2,1.0,0.05,0.80),
    ('V-20','a-priori',1,0.8,0.01,0.95),
    ('V-21','post-hoc',2,0.3,0.05,50),
    ('V-22','post-hoc',1,0.4,0.05,35),
    ('V-23','post-hoc',2,0.5,0.01,60),
    ('V-24','post-hoc',1,0.6,0.05,25),
    ('V-25','post-hoc',2,0.2,0.05,100),
    ('V-26','post-hoc',1,0.7,0.01,30),
    ('V-27','post-hoc',2,0.8,0.05,20),
    ('V-28','post-hoc',1,0.3,0.01,80),
    ('V-29','post-hoc',2,0.4,0.05,120),
    ('V-30','post-hoc',1,0.5,0.05,45),
]

def main():
    rows = []
    for case_id, mode, tails, dz, alpha, value in CASES:
        args = [sys.executable, 'cli.py', '--test', 't-paired', '--mode', mode,
                '--tails', str(tails), '--dz', str(dz), '--alpha', str(alpha)]
        args += ['--power', str(value)] if mode == 'a-priori' else ['--n_total', str(value)]
        proc = subprocess.run(args, text=True, capture_output=True)
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {'error': proc.stdout.strip() or proc.stderr.strip()}
        row = {'id': case_id, 'mode': mode, 'tails': tails, 'dz': dz,
               'alpha': alpha, 'input_power_or_n': value, 'exit_code': proc.returncode,
               'n_total': result.get('n_total', value if mode == 'post-hoc' else ''),
               'df': result.get('df', ''), 'ncp': result.get('ncp', ''),
               'critical_t': result.get('critical_t', ''),
               'actual_power': result.get('actual_power', result.get('power', '')),
               'error': result.get('error', '')}
        rows.append(row)
        print(f"{case_id} {mode:8} N={str(row['n_total']):>4} df={str(row['df']):>4} "
              f"ncp={str(row['ncp']):>18} critical_t={str(row['critical_t']):>18} "
              f"power={row['actual_power']} exit={proc.returncode}")
    output = Path('evidence') / 'v11_v30_cli_results.csv'
    output.parent.mkdir(exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print(f'\nSaved: {output}')
    print('Note: This records CLI results only; screenshot comparison must be checked separately.')

if __name__ == '__main__':
    main()
