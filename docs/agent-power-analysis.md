# Ollama ajanı — tek power_analysis sözleşmesi

24 Ekim 2026 tarihinde ajan mevcut CLI ile aynı JSON'u veren tek `power_analysis` MCP aracına uyarlandı. Git komutu çalıştırılmadı. Motor, CLI, SPEC ve diğer grup üyelerinin testleri değiştirilmedi.

## Çalıştırma

Ollama yerel olarak açık ve `qwen2.5:7b` kurulu olmalıdır. Bu uyarlama sırasında kapalı olan servis gizli arka plan süreci olarak başlatıldı ve model listede doğrulandı.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-agent.txt -r requirements-dev.txt
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m agent
```

Çıkış: `çıkış` / `exit`; yeni hesaplama: `yeni`. Sunucuyu ayrıca başlatmak gerekmez. `--verbose` gerçek MCP istek/cevaplarını stderr'e kaydeder.

## Örnekler

A-priori:

> dz=0.5, alpha=0.05, güç %80, çift yönlü test için kaç katılımcı gerekir?

Araç argümanları:

```json
{"test":"t-paired","mode":"a-priori","tails":2,"dz":0.5,"alpha":0.05,"power":0.8}
```

Beklenen gerçek MCP sonucu N=34; JSON alanları `ncp`, `critical_t`, `df`, `n_total`, `actual_power`.

Post-hoc:

> Post-hoc analiz: dz=0.5, alpha=0.05, n_total=45, tek yönlü. Ulaşılan güç nedir?

```json
{"test":"t-paired","mode":"post-hoc","tails":1,"dz":0.5,"alpha":0.05,"n_total":45}
```

Beklenen güç yaklaşık %95.1240; JSON alanları `ncp`, `critical_t`, `df`, `power`. Mevcut CLI bu modun çıktısında `n_total` döndürmez; ajan gösterdiği katılımcı sayısını doğrulanmış girdiden alır, MCP cevabına alan eklemez.

Klinik giriş:

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, farkların standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

Bu sorgu da aynı `power_analysis` aracına dz=0.5 ile gönderilir. Klinik verilerden **yalnızca dz türetmek** için mevcut `core_engine.calculate_dz_from_differences` / `calculate_dz_from_groups` yardımcıları yerel olarak yeniden kullanılır. Formüller yeniden yazılmadı; LLM hesaplama yapmaz. **N ve güç hesabı daima gerçek MCP sunucusunda** yapılır. Tek MCP aracının CLI sözleşmesinde klinik alanlar bulunmadığından bu alanlar araca gönderilmez.

## Güvenilirlik ve çok turlu kullanım

- Discovery yalnızca `power_analysis` kabul eder. Eski üç araç adı reddedilir.
- `tails` MCP'de tam sayı 1/2, `n_total` tam sayı, diğer sayısal alanlar sonlu JSON sayısıdır. Metin/bool/null reddedilir.
- A-priori için `power`, post-hoc için `n_total` zorunludur. İkisi aynı analizde birlikte gönderilmez.
- Açık post-hoc ifadesi veya verilen n_total post-hoc akışını belirler; hedef güç verilen örneklem hesabı a-priori akışıdır. Çelişen girdilerde kullanıcıdan netleştirme istenir.
- Eksik alpha, güç, yön, n_total, ortalama veya korelasyon uydurulmaz. Örneğin `Post-hoc dz=0.5 alpha=0.05 çift yönlü` sorusundan sonra ajan n_total ister; ikinci mesajda `34` ile tamamlanabilir.
- Ayrı ölçümlerin SD'si fark SD'si sayılmaz. Eksik grup ortalamaları/korelasyon tamamlanmadan dz türetme veya MCP hesaplama çağrısı yapılmaz. SD türü belirsizse açıklama istenir.
- Konuşma geçmişi girdi netleştirme için korunur. **Modelin araç seçimi aşamasına yalnızca doğrulanmış CLI argümanları verilir.** Ham klinik alanlar geçmişten araç parametrelerine karışmaz.
- Modelin araç adı ve argümanları şema ve doğrulanmış tabloyla birebir karşılaştırılır. Fazla alanlar sessizce silinmez; uydurma/yanlış çağrı reddedilir.
- Sonuç `n_total`/`ncp` veya post-hoc `power` alanlarından deterministik Türkçe metne dönüştürülür; modelin serbest metni hesaplama cevabı olarak gösterilmez.

## Testler

```powershell
$env:RUN_OLLAMA_TESTS = '1'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
.\.venv\Scripts\python.exe -m pytest -q
```

Eski üç araç sözleşmesine ait entegrasyon testleri yeni tek araç/JSON sözleşmesine taşındı. Diğer grup üyelerinin motor/CLI testlerine dokunulmadı. Post-hoc, eksik n_total, yanlış moda ait argüman, çıktı tutarlılığı ve ham klinik alanların model isteğine karışmaması için yeni kontroller eklendi.

İlk canlı tam çalıştırmada **173 başarılı, 2 başarısız** sonuç alındı. İki hata, çok turlu geçmişteki klinik alanların model tarafından araç çağrısına eklenmesiydi; şema doğrulaması MCP çağrısını engelledi. Yalnız doğrulanmış CLI tablosunu modelin araç aşamasına verme düzeltmesinden sonra hedefli **20 test geçti**. Ardından tam paket **176 başarılı, 0 başarısız, 0 atlanan; 73.44 saniye** ile tamamlandı. Buna **9 gerçek Ollama/MCP testi** dahildir. [Gerçek terminal kaydı](evidence/agent-single-tool-tests.txt). Önceki aşama raporları önceki protokolün tarihsel sonuçlarıdır.

Uyarlanmış doğrulama betiğinin `negative` komutu da yeniden çalıştırıldı: **9 PASS, 0 FAIL**, çıkış kodu 0. [Negatif kontrol kaydı](evidence/negative-scenarios.json). Git kullanan `audit` komutu bu çalışma sırasında çalıştırılmadı.

Doğrulanan ortam: Python 3.13.4, MCP 1.30.0, Ollama Python istemcisi 0.6.3, NumPy 2.2.6, SciPy 1.16.3. Proje `.venv` ortamı bu bilgisayardaki temel bilimsel paketleri system-site-packages üzerinden kullanır; yeni kurulumlarda requirements dosyalarıyla bağımsız ortam kurulabilir.
