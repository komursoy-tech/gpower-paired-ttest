# Nihai entegrasyon raporu — semantik SD düzeltmesi

**Tarih:** 22 Ekim 2026  
**Dal:** `codex/mcp-server-phase1`  
**Durum:** Raporlanan hata yeniden üretildi, deterministik semantik kontrolde düzeltildi ve gerçek Ollama/MCP ile doğrulandı. Commit/push yapılmadı.

## 1. Gerçek sonuçlar

- **135 başarılı, 0 başarısız, 0 atlanan pytest vakası; 40.16 saniye.**
- Önceden mevcut **109 testin tamamı** değişmeden yeniden geçti.
- Eklenen **26 regresyon:** 24 semantik/gerçek MCP kontrolü ve 2 canlı Ollama + MCP çok turlu senaryo.
- Toplam **7 canlı model testi** `RUN_OLLAMA_TESTS=1` ile çalıştı; atlanmadı.
- Önceki **9 negatif kontrolün tamamı geçti**. Düzeltme öncesi bu turda da 8 PASS / 1 FAIL sonucu yeniden üretildi; kanıt silinmedi.
- Açık fark SD'siyle gerçek terminal demosu ve SDK çağrısı N=34 üretti. `pip check`: bozuk bağımlılık yok.

[Tam terminal çıktısı](evidence/pytest-full.txt):

```text
135 passed in 40.16s

EXIT_CODE=0
```

| Test dosyası | Adet | Gerçek/mock ayrımı |
|---|---:|---|
| `test_core.py`, `test_cli.py`, `test_validation.py` | 26 | Gerçek motor ve CLI |
| `test_mcp_server.py` | 35 | Gerçek stdio, adaptör validasyonu ve ayrıca spy kontrolleri |
| `test_agent.py` | 43 | Birim/HTTP-model hata enjeksiyonu; gerçek MCP kullanan kontroller |
| `test_agent_live.py` | 5 | Gerçek qwen2.5:7b + MCP; terminal kapanışı dahil |
| `test_semantic_validation.py` | 24 | Semantik kurallar; mock model ve gerçek MCP çağrı gözlemleri |
| `test_semantic_live.py` | 2 | Gerçek model; eksik bilgi tamamlanmadan sıfır, tamamlanınca bir gerçek MCP çağrısı |
| **Toplam** | **135** | **0 başarısız / 0 skip** |

Mock model çıktıları gerçek Ollama başarısının kanıtı sayılmadı. Canlı kontroller iki ayrı dosyada açıkça `PASSED` görünür. Testlerin geçmesi bütün olası Türkçe ifadelerin doğruluğunu garanti etmez.

## 2. Hatanın yeniden üretilmesi ve kök nedeni

[Önceki nihai raporun arşivi](final-integration-report-before-semantic.md) incelendi. Düzeltme yapılmadan önce mevcut `negative` doğrulayıcısı yeniden çalıştırıldı ve hatanın devam ettiği gözlendi.

Sorgu:

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, her bir ölçümün standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

[Bu turdaki düzeltme öncesi gerçek kanıt](evidence/semantic-before-negative.json): `single_measurement_sd_must_be_clarified=FAIL`, `sd_diff=10` ile `calculate_from_differences` çağrısı ve N=34. Doğrulayıcı 8 PASS / 1 FAIL üreterek 1 çıkış koduyla tamamlandı.

Kök neden `agent/inputs.py` içindeki genel geri dönüş kuralıydı: `mean_diff` biliniyorsa herhangi bir `standart sapma` sayısını `sd_diff` olarak kabul ediyordu. “Ölçümün” sözcüğü ve SD'nin neye ait olduğu dikkate alınmıyordu. Yanlış eşleme modelin doğrulanmış girdi tablosuna da aktarıldığı için sonradan model argümanlarının tabloya eşit olması semantik hatayı önlemiyordu. Matematik motorunda veya MCP hesaplamasında hata yoktu.

## 3. Küçük ve doğrulanabilir düzeltme

Yalnızca iki uygulama dosyasının davranışı değişti:

### `agent/inputs.py`

- Açık `sd_diff`, “farkların standart sapması” ve “farkın standart sapması” fark SD'si olarak kabul edilir.
- “Her bir/her/her iki ölçümün standart sapması” yalnızca açıkça ortak verilen `sd1` ve `sd2` değerlerini sağlar. Bunlardan `sd_diff`, ortalamalar veya korelasyon hesaplanmaz/tahmin edilmez.
- Fark ortalaması tek başına genel bir SD'ye anlam atamak için yeterli değildir. Tanınmayan/tek ölçüme ait SD ifadeleri fark SD'si olmaz.
- Önceden çalışan “farkı 5 ..., standart sapması 10” iyelikli biçimi yalnızca aynı dar ifade bağı içinde korunur. Açıkça sorulmuş bir fark SD'si sorusuna verilen doğrudan yanıt da desteklenir. Ölçüm/grup ifadesi varsa bu kısa yol uygulanmaz.
- Grup istatistikleri bulunup açık fark SD'si bulunmadığında grup yöntemi seçilir. Bilinen fark ortalaması, grup ortalamalarının tahmin edilmesine yol açmaz.

### `agent/orchestrator.py`

- SD'nin anlamı belirsizse soru sorulur ve model/MCP çağrısından önce durulur. Önceden önbelleğe alınmış SD'ler bu belirsizliği aşmak için yeniden kullanılmaz.
- Tür sorusuna sadece `10` gibi bir sayı vermek SD türünü açıklamış sayılmaz. Yalnızca açık bir fark SD'si sorusundan sonra sayısal yanıt o alana bağlanabilir.
- Kullanıcı daha sonra açık fark SD'si verirse yöntem netleştirilir; eski grup SD'leri bu seçime karışmaz. Grup SD'si verdiğinde de eski fark SD'si kullanılmaz.
- Eksik bilgilerin tamamlanması için diğer açık girdiler korunur. Grup yöntemi için `mean1`, `mean2`, `sd1`, `sd2`, `correlation`, alpha, güç ve yön tamamlanmadan araç çağrılmaz.

LLM sistem promptu değiştirilmedi; çözüm prompta eklenen bir uyarıya dayanmıyor. İstatistiksel formül, korelasyon varsayılanı veya MCP hesaplama davranışı eklenmedi.

## 4. Önceki başarısız kontrolün yeni sonucu

[Düzeltme sonrası aynı dokuz negatif kontrol](evidence/negative-scenarios.json):

```json
{
  "scenario": "single_measurement_sd_must_be_clarified",
  "status": "PASS",
  "message": "Hesaplama için eksik veya net olmayan bilgileri belirtin: öncesi ortalama (mean1), sonrası ortalama (mean2), korelasyon (correlation). Değerleri tahmin etmeyeceğim.",
  "mcp_calls": [],
  "execution": null
}
```

| Negatif kontrol | Önce | Sonra |
|---|---|---|
| Eksik test yönü | PASS | PASS |
| Birden fazla farklı SD | PASS | PASS |
| Alpha=1 | PASS | PASS |
| Uydurma araç adı | PASS | PASS |
| Eksik `sd_diff` argümanı | PASS | PASS |
| Sayı yerine metin argümanı | PASS | PASS |
| Her bir ölçümün SD'si | **FAIL: gerçek ama yanlış girdili N=34** | **PASS: soru, sıfır çağrı** |
| Ollama bağlantı reddi | PASS | PASS |
| MCP bağlantı kapanışı | PASS | PASS |
| **Toplam** | **8 PASS / 1 FAIL** | **9 PASS / 0 FAIL** |

Kontrol programı düzeltme sonrasında 0 çıkış koduyla tamamlandı. Hatalı araç çıktıları için kontrollü model enjeksiyonu kullanıldı; gerçek MCP sunucusu korundu. Tek ölçüm SD'si senaryosunda gerçek Ollama bağlantısı açılır, fakat yetersiz bilgi nedeniyle modelden araç istenmez. Bunun devamının gerçekten çalıştığını aşağıdaki canlı çok turlu regresyonlar ayrıca kanıtlar.

## 5. Çok turlu ve gerçek MCP kabulü

`test_semantic_live.py` gerçek resmî Ollama istemcisi ve yerel qwen2.5:7b kullanır. SDK `call_tool` fonksiyonu gözlemlenir; cevap mock edilmez:

1. Hatalı sorgudaki ortak ölçüm SD'si verilince MCP çağrı sayısı **0** olur; ortalamalar ve korelasyon sorulur. Kullanıcı `mean1=140 mean2=135 correlation=0.5` verdiğinde model `calculate_from_groups` seçer. **Bir** gerçek MCP çağrısı N=34 döndürür; argümanlarda `sd_diff` bulunmaz.
2. Türü belirsiz `standart sapma 10` verilince yine **0** çağrı yapılır. Kullanıcı “Farkların standart sapması 10” dediğinde `calculate_from_differences` ile **bir** gerçek çağrı N=34 üretir.

Diğer regresyonlar: yalnızca korelasyonun ikinci mesajda verilmesi, ortalamalar hâlâ eksikken çağrı yapılmaması, açık fark SD'sine geçiş, tür sorusuna tek sayı verilmesi, önbellekteki eski SD'nin iptali, sıfır/negatif fark SD'sinin gerçek motor tarafından reddi ve önceki N=34 senaryosunun korunması.

## 6. Gerçek terminal demosu

[Yeni terminal kaydı](evidence/demo-terminal.txt) ve [yeni gerçek SDK cevabı](evidence/demo-mcp-receipt.json) düzeltme sonrasında tekrar oluşturuldu. Sorgu:

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, farkların standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

Araç: `calculate_from_differences`. Girdiler: `mean_diff=5`, `sd_diff=10`, `alpha=0.05`, `target_power=0.8`, `tails="two-tailed"`.

```json
{
  "sample_size": 34,
  "df": 33,
  "delta": 2.9154759474226504,
  "critical_t": 2.0345152974493383,
  "actual_power": 0.8077775012792737
}
```

`isError=false`. Terminal `çıkış` ile 0 koduyla kapandı. Terminal ve ayrı SDK gözlemi iki ayrı gerçek çalıştırmadır; uygulama UUID'leri JSON-RPC protokol id'si olarak sunulmaz.

## 7. Çalıştırılan komutlar ve ortam

```powershell
# Düzeltmeden önce: hata yeniden üretildi (8 PASS / 1 FAIL).
.\.venv\Scripts\python.exe -m scripts.verify_delivery negative

# İlk hedefli doğrulama: 67 geçti (24 yeni + 43 mevcut ajan testi).
.\.venv\Scripts\python.exe -m pytest tests/test_semantic_validation.py tests/test_agent.py -q

# Gerçek model açık tam paket: 135 geçti.
.\.venv\Scripts\python.exe -m scripts.verify_delivery suite

# Düzeltmeden sonra: 9/9 negatif ve gerçek N=34 demosu.
.\.venv\Scripts\python.exe -m scripts.verify_delivery negative
.\.venv\Scripts\python.exe -m scripts.verify_delivery demo
.\.venv\Scripts\python.exe -m scripts.verify_delivery audit
```

`suite` gerçek alt süreçte `RUN_OLLAMA_TESTS=1`, `OLLAMA_MODEL=qwen2.5:7b`, yerel `OLLAMA_HOST` ile `python -m pytest -q -rA --tb=short`, ardından `python -m pip check` çalıştırır. Tam test komutu elle de çalıştırılabilir:

```powershell
$env:RUN_OLLAMA_TESTS = '1'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
.\.venv\Scripts\python.exe -m pytest -q -rA --tb=short
```

[Ortam kaydı](evidence/environment.json): Windows, Python 3.13.4, MCP SDK 1.30.0, Ollama Python 0.6.3 / CLI 0.33.3, Pydantic 2.14.1, NumPy 2.5.4, SciPy 1.18.1, pytest 9.1.1. Bu turda paket yüklenmedi. [Pip kontrolü](evidence/pip-check.txt) temiz.

## 8. Korunan dosyalar ve değişiklik kapsamı

`SPEC.md`, `core_engine.py`, `cli.py`, mevcut MCP sunucusu ve eski 109 testin kaynakları değiştirilmedi. Mevcut kullanıcı değişiklikleri korundu. Eski kaynaklarla karşılaştırıldığında yalnızca `agent/inputs.py` ve `agent/orchestrator.py` değişti; iki yeni regresyon dosyası eklendi. Bağımlılıklar aynı kaldı.

[Değişiklik ve test karşılaştırması](evidence/semantic-regression-summary.json), düzeltme öncesi hash'lerle mevcut dosyaları karşılaştırır ve eski 109 test kimliğinin yeni başarılı listede bulunduğunu kontrol eder. [Son kabul çalıştırması boyunca bütünlük](evidence/protected-integrity.json) ve [aday dosya taraması](evidence/repository-audit.json) ayrıca kaydedilir. Kişisel yol/anahtar örüntü taraması tam bir gizli bilgi veya Git geçmişi denetimi değildir. JPG kanıtları çözümlenmedi; yerel `.venv` ve önbellek ignored durumdadır.

Dokümantasyon: bu nihai rapor, README ve ajan kullanım açıklaması güncellendi. Önceki rapor [arşivde](final-integration-report-before-semantic.md), eski 109 test çıktısı [önceki logda](evidence/pytest-before-semantic.txt), bu turdaki gerçek hata yeniden üretimi [önceki negatif kayıtta](evidence/semantic-before-negative.json) korunur. Ana evidence dosyaları güncel sonuçları gösterir.

## 9. Teslim kontrol listesi ve sınırlar

- [x] Hata kod değişikliğinden önce gerçek çağrıyla yeniden üretildi.
- [x] Çözüm deterministik ve test edilebilir semantik katmanda uygulandı.
- [x] Tek ölçüm SD'si `sd_diff` olarak gönderilmiyor.
- [x] Ortalamalar ve korelasyon tahmin edilmiyor; yetersiz bilgide soru soruluyor.
- [x] Belirsizlik netleştirilmeden ve eksikler tamamlanmadan MCP çağrılmıyor.
- [x] Önceki 109 testin tamamı ve 26 yeni regresyon geçti.
- [x] Gerçek Ollama + MCP testleri çalıştı; 0 skip.
- [x] Önceki 9 negatif kontrolün tamamı tekrar geçti; eski FAIL saklandı.
- [x] Korunan motor, SPEC, CLI ve MCP hesaplama davranışı değiştirilmedi.
- [ ] Grup teslim dosyalarını ve mevcut untracked dosyaları gözden geçirip stage kapsamını belirlesin.
- [ ] Yüklemeden önce `.env`, anahtar, kişisel yol ve model dosyaları yeniden kontrol edilsin.
- [ ] Commit/push grup kararıyla yapılsın; bu çalışma bunları içermez.

Doğal dil katmanı sınırlı etiket/örüntü kurallarıyla çalışır; her dilsel ifadeyi çözümlediği iddia edilmez. Tanınmayan SD türü açık alan adıyla netleştirilmelidir. Aynı kullanıcı mesajında farklı giriş yöntemleri birlikte açıkça verilirse yöntem seçimi istenebilir. Farklı model/sürüm veya donanımda canlı testler tekrarlanmalıdır. Transitif paketler tamamen kilitli değildir; mevcut minimal N testi N−1 gücünü bağımsız sınamaz. Bu sınırlamalar giderilmiş gibi sunulmamıştır.
