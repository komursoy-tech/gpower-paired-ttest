"""CONTRACT.md 1.0.0 K2 CLI checks."""
import json
import pytest
from cli import run

AP = ['--test','t-paired','--mode','a-priori','--tails','1','--dz','0.5','--alpha','0.05','--power','0.95']
PH = ['--test','t-paired','--mode','post-hoc','--tails','1','--dz','0.5','--alpha','0.05','--n_total','45']

def invoke(capsys, args):
    code = run(args)
    out = capsys.readouterr()
    assert not out.err
    assert len(out.out.strip().splitlines()) == 1
    return code, json.loads(out.out)

@pytest.mark.parametrize('args,key', [(AP,'actual_power'), (PH,'power')])
def test_public_k2_vectors(capsys, args, key):
    code, result = invoke(capsys, args)
    assert code == 0
    assert result['df'] == 44
    assert result['ncp'] == pytest.approx(3.3541020, abs=1e-6)
    assert result['critical_t'] == pytest.approx(1.6802300, abs=1e-6)
    assert result[key] == pytest.approx(.9512400, abs=1e-6)
    if key == 'actual_power':
        assert result['n_total'] == 45

@pytest.mark.parametrize('args,expected,field', [
    (AP[:6]+AP[8:], 'MISSING_PARAM','dz'),
    (AP[:8]+AP[10:], 'MISSING_PARAM','alpha'),
    (AP[:-2], 'MISSING_PARAM','power'),
    (PH[:-2], 'MISSING_PARAM','n_total'),
    (AP+['--n_total','45'], 'UNKNOWN_PARAM','n_total'),
    (PH+['--power','0.95'], 'UNKNOWN_PARAM','power'),
    (AP+['--other','1'], 'UNKNOWN_PARAM','input'),
    (AP+['--effect-size','0.5'], 'UNKNOWN_PARAM','input'),
    (AP[:5]+['3']+AP[6:], 'OUT_OF_RANGE','tails'),
    (AP[:5]+['1.5']+AP[6:], 'INVALID_VALUE','tails'),
    (AP[:7]+['0']+AP[8:], 'OUT_OF_RANGE','dz'),
    (AP[:9]+['1']+AP[10:], 'OUT_OF_RANGE','alpha'),
    (AP[:-1]+['nan'], 'INVALID_VALUE','power'),
    (PH[:-1]+['45.5'], 'INVALID_VALUE','n_total'),
    (PH[:-1]+['1'], 'OUT_OF_RANGE','n_total'),
    (['--test','other','--mode','a-priori'], 'UNSUPPORTED','test'),
    (['--test','t-paired','--mode','criterion'], 'UNSUPPORTED','mode'),
    (['--mode','a-priori'], 'MISSING_PARAM','test'),
])
def test_errors(capsys, args, expected, field):
    code, result = invoke(capsys, args)
    assert code == 2
    assert result['code'] == expected
    assert result['field'] == field
    assert result['error']

def test_version(capsys):
    code, result = invoke(capsys, ['--version'])
    assert code == 0
    assert result['contract_version'] == '1.0.0'
    assert result['name'] and result['engine']
