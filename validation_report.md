# [REA] G*Power Bağımsız Doğrulama Raporu — Görev 2 (K2)

**Güncelleme:** 24 Ekim 2026
**Referans uygulama:** G*Power 3.1.9.7 (Windows)
**Test:** t tests → Means: Difference between two dependent means (matched pairs)
**Sözleşme:** CONTRACT.md 1.0.0 (`t-paired`)
**Yerel ortam:** Windows, Python 3.14.3, pytest 9.1.1 (kullanıcı terminal kaydı). NumPy ve SciPy sürümleri bu raporda doğrulanmadı.

## G*Power ekran görüntüleri ve sonuçlar

Aşağıdaki V-01–V-05 a-priori gözlemleri önceki doğrulama kaydından korunmuştur. V-06, kullanıcının doğrudan sağladığı G*Power post-hoc ekran görüntüsüyle doğrulanmıştır.

| ID | Mod | Tails | dz | α | Hedef güç / verilen N | G*Power N | df | G*Power güç | Kanıt |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| V-01 | a-priori | 2 | 0.5 | 0.05 | güç 0.80 | 34 | 33 | 0.8077775 | [V-01](evidence/V-01.JPG) |
| V-02 | a-priori | 2 | 0.2 | 0.05 | güç 0.80 | 199 | 198 | 0.8016910 | [V-02](evidence/V-02.JPG) |
| V-03 | a-priori | 2 | 0.8 | 0.05 | güç 0.95 | 23 | 22 | 0.9558497 | [V-03](evidence/V-03.JPG) |
| V-04 | a-priori | 1 | 0.5 | 0.05 | güç 0.80 | 27 | 26 | 0.8118316 | [V-04](evidence/V-04.JPG) |
| V-05 | a-priori | 2 | 0.3 | 0.01 | güç 0.90 | 169 | 168 | 0.9006992 | [V-05](evidence/V-05.JPG) |
| V-06 | post-hoc | 1 | 0.5 | 0.05 | N = 45 | 45 | 44 | 0.9512400 | [V-06](evidence/V-06.JPG) |

### V-06: bağımsız post-hoc karşılaştırması

G*Power ekran görüntüsünde `tails=1`, `dz=0.5`, `alpha=0.05`, `n_total=45` girildi. Çıktılar: `ncp=3.3541020`, `critical_t=1.6802300`, `df=44`, `power=0.9512400`.

Aynı parametrelerle kullanıcı terminalinde çalıştırılan CLI:

```cmd
python cli.py --test t-paired --mode post-hoc --tails 1 --dz 0.5 --alpha 0.05 --n_total 45
```

```json
{"ncp":3.3541019662496847,"critical_t":1.6802299765721171,"df":44,"power":0.9512400452506585}
```

| Alan | G*Power | CLI | Mutlak fark |
|---|---:|---:|---:|
| ncp | 3.3541020 | 3.3541019662496847 | 3.38e-8 |
| critical_t | 1.6802300 | 1.6802299765721171 | 2.34e-8 |
| df | 44 | 44 | 0 |
| power | 0.9512400 | 0.9512400452506585 | 4.53e-8 |

**Sonuç:** V-06 için tam sayı eşleşmesi sağlandı; ondalık farklar CONTRACT.md §6'daki `1e-6` toleransının altında. A-priori için de sözleşmenin açık K2 vektörü (`tails=1`, `dz=0.5`, `alpha=0.05`, `power=0.95`) kullanıcı CLI çıktısıyla eşleşti: `n_total=45`, `df=44`, `actual_power=0.9512400452506585`. Bu ikinci eşleşme, V-06'dan ayrı yeni bir G*Power ekran görüntüsü olarak sayılmıyor.

## Otomatik testler

Kullanıcının son terminal kaydı:

```cmd
python -m pytest tests/test_core.py tests/test_cli.py tests/test_validation.py -v
```

**46 passed in 1.93s.** Kapsam: `test_core.py`, `test_cli.py`, `test_validation.py`. Bu sonuç bütün projenin MCP/ajan testlerinin geçtiği anlamına gelmez; tam `pytest -q` çalıştırması MCP bağımlılık/sürüm uyumsuzluğundan etkilenmişti.

## Tekrarlama komutları (CONTRACT.md 1.0.0)

```cmd
python cli.py --version
python cli.py --test t-paired --mode a-priori --tails 1 --dz 0.5 --alpha 0.05 --power 0.95
python cli.py --test t-paired --mode post-hoc --tails 1 --dz 0.5 --alpha 0.05 --n_total 45
python -m pytest tests/test_core.py tests/test_cli.py tests/test_validation.py -v
```

## Sınırlar ve takip işleri

- Altı G*Power ekran görüntüsü toplamı, ödevde belirtilen 30+ bağımsız ekran görüntüsü hedefinin yerine geçmez. Hedefin takım geneli mi kişi bazında mı uygulandığı ödev yönergesiyle ayrıca kontrol edilmelidir.
- Bu rapordaki altı vektörün eşleşmesi gizli testlerin tamamının geçeceğini garanti etmez. Sınır durumları, çift kuyruk, hatalı girdiler ve diğer aileler ayrı test edilmelidir.
- `SPEC.md` veya pytest içindeki sayısal vektörler, tek başına bağımsız G*Power gözlemi olarak sayılmadı.
- Bu rapor mevcut kanıtları kaydeder; MCP ve ajan kodlarını değiştirmez.

## Differential Validation — 700 Test Cases

**Date:** 24 October 2026
**Test family:** t tests — Difference between two dependent means (matched pairs)
**Contract:** v1.0.0
**Validation script:** `differential_validation_v3.py`
**Results file:** `evidence/differential_results.csv`

### Results

| Metric | Result |
|---|---|
| Total test cases | 700 |
| Passed | 700 |
| Failed | 0 |
| Tolerance | 1e-6 |
| SciPy nct fallback cases | 0 |
| Chi-square quadrature cases | 84 |

### Validation Method

The implementation was compared against reference calculations using statsmodels, SciPy, and numerical integration.

For 84 cases where the initial reference computation produced NaN, chi-square numerical quadrature was used as an alternative.

All 700 comparisons passed within the specified tolerance.

### Limitations

These results do not constitute 700 fully independent G*Power oracle comparisons. The numerical integration method shares mathematical and computational components with the project's core engine.

Independent G*Power screenshot-based validation is tracked separately.