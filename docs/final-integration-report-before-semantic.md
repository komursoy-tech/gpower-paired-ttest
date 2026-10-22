> Arşiv: Bu belge düzeltme öncesi Aşama 3 bulgularını korur. Güncel sonuçlar final-integration-report.md içindedir. Demo alıntıları önceki çalıştırmaya aittir; ana demo dosyaları en son çalıştırmayı gösterir.

# Nihai MCP + Ollama entegrasyon doğrulama raporu

**Tarih:** 22 Ekim 2026  
**Dal:** `codex/mcp-server-phase1`  
**Kapsam:** Mevcut sistemi yeniden doğrulama, gerçek demo, bağımsız negatif kontroller ve teslim dokümantasyonu. Uygulama veya mevcut test davranışı değiştirilmedi. Commit/push yapılmadı.

## Kabul durumu

**Mevcut test paketi: 109 başarılı, 0 başarısız, 0 atlanan.** Gerçek model testleri `RUN_OLLAMA_TESTS=1` ile açık çalıştırıldı. Kullanıcının verdiği tam doğal dil sorgusu gerçek terminal ajanında N=34 üretti. Üç MCP aracı ve yerel `qwen2.5:7b` tool calling akışı çalışıyor.

**Bağımsız ek negatif kontroller: 8 başarılı, 1 başarısız.** Tek ölçümün SD'sinin fark SD'si olarak kabul edilebildiği doğrulandı. Bu nedenle serbest doğal dil için bütün güvenilirlik kriterlerinin karşılandığı veya teslimin koşulsuz hazır olduğu söylenemez. Sorun bu raporda açıkça kaydedildi; doğrulama aşaması kapsamında uygulama sessizce değiştirilmedi.

Bu iki sonuç ayrı değerlendirilmelidir. Ek kontroller mevcut 109 pytest vakasına dahil değildir; pytest sonucu bu açığı kapsamadığı için geçmektedir.

## 1. Oluşturulan dosyalar ve korunan çalışma

Bu aşamada eklenenler:

- `README.md`: amaç, mimari, Windows kurulumu, kullanım, örnekler, testler ve sınırlamalar.
- `docs/final-integration-report.md`: bu rapor.
- `scripts/verify_delivery.py`: uygulamadan ayrı, tekrar çalıştırılabilir teslim doğrulaması; `suite`, `demo`, `negative`, `audit` komutları.
- `docs/evidence/pytest-before-semantic.txt`: 109 testin her birinin durumu ve gerçek terminal çıktısı.
- `docs/evidence/pip-check.txt`: bağımlılık kontrolü.
- `docs/evidence/environment.json`: kullanılan sürümler.
- `docs/evidence/demo-terminal.txt`: tam demo sorgusu, stdout, stderr, çıkış kodu.
- `docs/evidence/demo-mcp-receipt.json`: gerçek SDK çağrısının argümanları ve alınan `CallToolResult`.
- `docs/evidence/semantic-before-negative.json`: başarısız kontrol dahil tüm negatif sonuçlar.
- `docs/evidence/protected-before.json`, `protected-integrity.json`: korunan dosyaların SHA-256 kaydı ve karşılaştırması.
- `docs/evidence/repository-audit.json`: aday dosyalarda kişisel yol/anahtar/binary örüntü taraması.

`SPEC.md`, `core_engine.py`, `cli.py`, mevcut bütün testler, MCP ve ajan kaynakları, bağımlılık dosyaları, plan ve önceki doğrulama raporu korunmuştur. Hash karşılaştırmasında `changed: []` görülmüştür. Hash koruması bu aşamada alınan başlangıç durumuna göredir; sürüm geçmişinin bağımsız denetimi değildir.

Başlangıçta Aşama 1 ve 2 dosyaları zaten Git'te untracked durumdaydı. Bu durum korunmuştur; bu rapor onların daha önce commit edildiğini veya GitHub'a yüklendiğini iddia etmez. README mevcut değildi; yeni oluşturuldu.

## 2. Gerçekten çalıştırılan doğrulama komutları

Repository kökünde mevcut `.venv` ile:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_delivery suite
.\.venv\Scripts\python.exe -m scripts.verify_delivery demo
.\.venv\Scripts\python.exe -m scripts.verify_delivery negative
.\.venv\Scripts\python.exe -m scripts.verify_delivery audit
```

`suite` alt süreçte aşağıdaki gerçek komutları çalıştırdı:

```powershell
$env:RUN_OLLAMA_TESTS = '1'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
.\.venv\Scripts\python.exe -m pytest -q -rA --tb=short
.\.venv\Scripts\python.exe -m pip check
ollama --version
```

`demo`, `python -m agent --verbose` terminal alt sürecine kullanıcı sorgusunu ve `çıkış` komutunu iletti. Ayrıca gerçek Ollama ve MCP istemcisiyle aynı sorguyu yeniden çalıştırıp gerçek SDK cevabını kaydetti. `negative`, uygulama dosyalarını değiştirmeden kontrollü hataları sınadı. Git durum/kontrol komutları ve aday dosyalarda örüntü taraması da yapıldı. Bu aşamada paket kurulmadı.

## 3. Test sonuçları ve kanıtın kapsamı

[Gerçek terminal kaydı](evidence/pytest-before-semantic.txt) son satırları:

```text
109 passed in 36.49s

EXIT_CODE=0
```

[Bağımlılık kontrolü](evidence/pip-check.txt):

```text
No broken requirements found.

EXIT_CODE=0
```

| Dosya/kapsam | Adet | Sonuç | Gerçek/mock ayrımı |
|---|---:|---|---|
| `test_core.py` | 9 | Geçti | Gerçek motor |
| `test_cli.py` | 6 | Geçti | Gerçek CLI fonksiyonları |
| `test_validation.py` | 11 | Geçti | Gerçek motor; SPEC vektörleri |
| `test_mcp_server.py` | 35 | Geçti | Gerçek stdio testleri; ayrıca adaptör/spy kontrolleri |
| `test_agent.py` | 43 | Geçti | Birim kontrolleri; mock model/HTTP ile hata enjeksiyonu ve gerçek MCP |
| `test_agent_live.py` | 5 | Geçti | Gerçek Ollama modeli + gerçek MCP; terminal giriş/çıkış dahil |
| **Toplam** | **109** | **109 geçti** | **0 başarısız, 0 skip** |

Canlı dosyada her biri açıkça `PASSED` görünür:

```text
PASSED tests/test_agent_live.py::test_real_ollama_to_mcp[differences]
PASSED tests/test_agent_live.py::test_real_ollama_to_mcp[effect-size]
PASSED tests/test_agent_live.py::test_real_ollama_to_mcp[groups]
PASSED tests/test_agent_live.py::test_live_missing_parameter_followup
PASSED tests/test_agent_live.py::test_live_terminal_question_and_exit
```

Mock HTTP/model testleri canlı Ollama kanıtı olarak sunulmamıştır. Negatif testlerde beklenen hata mesajlarının görünmesi pytest başarısızlığı değildir. Buna karşılık aşağıdaki ek semantik kontrol gerçek bir kabul başarısızlığıdır.

## 4. Ortam sürümleri

[Makine tarafından kaydedilen ortam](evidence/environment.json):

| Bileşen | Sürüm |
|---|---|
| İşletim ortamı | Windows (`win32`) |
| Python | 3.13.4 |
| MCP SDK | 1.30.0 |
| Ollama Python istemcisi | 0.6.3 |
| Ollama CLI | 0.33.3 |
| Model | `qwen2.5:7b` |
| Pydantic | 2.14.1 |
| NumPy | 2.5.4 |
| SciPy | 1.18.1 |
| pytest | 9.1.1 |
| AnyIO | 4.15.1 |
| jsonschema | 4.26.0 |
| httpx | 0.28.1 |

Bu kayıt ortamın çalışan kombinasyonunu gösterir; başka sistemlerde aynı süre veya davranışı garanti etmez. Yerel model dosyaları repository'ye eklenmemiştir.

## 5. Gerçek demo ve MCP cevabı

Kullanıcının sorgusu değiştirilmeden sınandı:

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, farkların standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

[Terminal kaydı](evidence/demo-terminal.txt), stdout:

```text
G*Power ajanı hazır (qwen2.5:7b). Çıkış: çıkış / exit; yeni hesaplama: yeni.
Siz> MCP hesaplama sonucu: çift yönlü eşleştirilmiş t-testi için en az 34 tamamlanmış katılımcı/eşleşmiş çift gerekir.
Alpha: 0.05; hedef güç: %80.
Serbestlik derecesi (df): 33; delta: 2.915476; kritik t: 2.034515; ulaşılan güç: %80.7778.
Bu sayı tamamlanmış çiftleri belirtir; kayıp katılımcı payı eklenmemiştir.
```

Aynı terminal çalıştırmasının stderr kaydı:

```text
INFO:agent.orchestrator:MCP request id=bda23e48-ea95-4f1f-add9-5c7d0e2c27e8 tool=calculate_from_differences arguments={'mean_diff': 5.0, 'sd_diff': 10.0, 'alpha': 0.05, 'target_power': 0.8, 'tails': 'two-tailed'}
Processing request of type CallToolRequest
INFO:agent.orchestrator:MCP success id=bda23e48-ea95-4f1f-add9-5c7d0e2c27e8 result={'sample_size': 34, 'df': 33, 'delta': 2.9154759474226504, 'critical_t': 2.0345152974493383, 'actual_power': 0.8077775012792737}
```

Terminal çıkış kodu **0**. Uygulama istek UUID'si protokolün JSON-RPC id alanı olarak sunulmamıştır; uygulama loglarını ilişkilendiren kimliktir.

[Ayrı gerçek SDK gözlem kaydı](evidence/demo-mcp-receipt.json), `ClientSession.call_tool` çağrısını gözlemleyen ve asıl SDK fonksiyonunu gerçekten bekleyen bir sarmalayıcıyla oluşturuldu. Cevap veya hesaplama mock edilmedi. Tam `CallToolResult` içinde:

```json
{
  "structuredContent": {
    "sample_size": 34,
    "df": 33,
    "delta": 2.9154759474226504,
    "critical_t": 2.0345152974493383,
    "actual_power": 0.8077775012792737
  },
  "isError": false
}
```

Çağrılan araç `calculate_from_differences`; parametreler `mean_diff=5`, `sd_diff=10`, `alpha=0.05`, `target_power=0.8`, `tails="two-tailed"`. Bu ikinci çalıştırmanın UUID'si farklıdır; iki kayıt aynı çalıştırma gibi birleştirilmemiştir.

## 6. MCP araçları ve Ollama durumları

Discovery tam olarak üç aracı döndürdü. `calculate_sample_size`, `calculate_from_differences` ve `calculate_from_groups` canlı model testlerinde doğru seçildi; her biri gerçek MCP cevabında N=34 üretti. Çıktıların beş alanı ve şemaları Aşama 1 testlerinde doğrulandı.

Yerel model native tool calling üretti; yalnızca model metadata'sına bakılarak destek varsayılmadı. Kullanıcıya sonuç, modelin serbest metninden değil doğrulanan MCP cevabından deterministik olarak verildi. MCP stdin EOF ve terminal `çıkış` davranışı test edildi. Bu kapsam dışında uzak ağ/MCP HTTP dağıtımı doğrulanmadı.

## 7. Bağımsız negatif senaryolar

[Tam kayıt](evidence/semantic-before-negative.json). Doğrulayıcı **8 PASS, 1 FAIL** nedeniyle **1** çıkış koduyla sonlandı. Hatalı model çıktıları için `FixedModel` kullanıldı; gerçek MCP sunucusu değiştirilmedi. Semantik SD senaryosu ise gerçek `qwen2.5:7b` ile çalıştırıldı.

| Senaryo | Sonuç | Gözlenen davranış |
|---|---|---|
| Eksik test yönü | PASS | Soru soruldu; MCP çağrılmadı, sonuç yok |
| İki farklı standart sapma verilmesi | PASS | Belirsizlik hatası; MCP çağrılmadı |
| Alpha=1 | PASS | Gerçek MCP motor hatası; `execution=null`, sayısal sonuç yok |
| Uydurma araç adı | PASS | Allowlist reddi; MCP çağrılmadı |
| `sd_diff` eksik araç argümanı | PASS | Şema reddi; MCP çağrılmadı |
| `sd_diff="10"` yanlış tür | PASS | Şema reddi; MCP çağrılmadı |
| Tek ölçümün SD'si | **FAIL** | Açıklama sorulması gerekirken SD fark SD'si sayıldı ve gerçek MCP hesaplaması yapıldı |
| Ollama bağlantı reddi | PASS | Gerçek, dinlemeyen loopback uç noktasında anlaşılır bağlantı hatası |
| MCP bağlantısının kapanması | PASS | Gerçek alt süreç initialize öncesi kapandı; `McpError: Connection closed`, sonuç yok |

Bağlantı testleri kullanıcının çalışan Ollama servisini durdurmadı. Ollama için geçici port, MCP için yalnızca kontrol süresince SDK alt süreç argümanlarının enjeksiyonu kullanıldı. Bunlar dış servisin beklenmeyen ağ arızalarının tüm olası biçimlerini kapsamaz.

Başarısız MCP ve bağlantı çağrılarında hesaplama sonucu uydurulmadı. Bununla birlikte SD semantiği hatasında **başarılı gerçek bir hesaplama yanlış yorumlanmış girdilerle** yapıldı. Bu, uydurma tool cevabından farklıdır fakat istatistiksel olarak önemli bir güvenilirlik açığıdır.

### Açık bulgu: tek ölçüm SD'si ile fark SD'sinin karıştırılması

Tekrarlanabilir sorgu:

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, her bir ölçümün standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

Beklenen: farkların standart sapmasını istemek veya iki ölçümün SD'leri ve korelasyonunu netleştirmek; mevcut verilerle fark SD'sini varsaymamak.

Gözlenen: `sd_diff=10` kabul edilerek `calculate_from_differences` çağrıldı ve N=34 gösterildi. `agent/inputs.py` içindeki, fark ortalaması varsa niteliksiz `standart sapma` ifadesini fark SD'si sayan geri dönüş kuralı daha geniş ifadeleri de yakalıyor. Üstelik modelin doğrulanmış girdi tablosuna bu yanlış eşleme aktarılıyor; argüman eşitliği kontrolü anlam hatasını önlemiyor.

Teslim öncesi önerilen düzeltme: tek ölçüm/grup SD'sini fark SD'sinden ayırmak, belirsizlikte çağrıyı durdurup soru sormak ve bu örneği yeni regresyon testi olarak eklemek. Motor veya SPEC değişikliği gerekmez. Bu rapor düzeltmenin yapıldığını iddia etmez.

## 8. Güvenlik, dosya bütünlüğü ve clean-room sınırı

Kanıt dosyaları UTF-8 olarak yazıldı; kaydetmeden önce çalışma dizini/kullanıcı dizini önekleri ayıklandı. Hash kayıtları repository'ye göreli yollar kullanır. Ortam kaydı anahtarları, bütün ortam değişkenlerini veya kişisel yorumlayıcı yolunu dışa aktarmaz. Gösterilen veriler sentetik demo istatistikleridir.

[Dosya bütünlüğü kaydı](evidence/protected-before-semantic-integrity.json): `changed: []`. Sanal ortam ve pytest önbelleği Git tarafından ignored durumdadır. [Repository taraması](evidence/repository-audit.json) aday metinlerde kişisel kullanıcı yolu, belirli token/özel anahtar örüntüleri ve yerel binary/model dosyalarını kontrol etti; son kayıtta `findings: []` çıktı. Bu, kapsamlı bir gizli bilgi veya Git geçmişi denetimi değildir; JPG dosyaları içerik/metadata açısından çözümlenmemiştir. Önceden kullanıcı tarafından eklenen ekran görüntüleri değiştirilmedi. README ve bu raporun UTF-8 içeriği ve yerel bağlantıları ayrıca kontrol edildi; bozuk bağlantı bulunmadı.

`.env` dosyaları mevcut `.gitignore` tarafından genel olarak engellenmiyor. Bu aşamada böyle bir dosya oluşturulmadı veya eklenmedi; ileride oluşturulursa yüklenmemesi ayrıca kontrol edilmelidir. Tarama sonucunu, gelecekte eklenecek dosyaların güvenli olduğu garantisi olarak kullanmayın.

Bu aşamada GPower.exe/decompile çıktısı eklenmedi, orijinal uygulama incelenmedi. SPEC ve bağımsız motor kullanıldı; önceki doğrulama kayıtlarının sınırları korunur.

## 9. Demo komutları

Kurulu ortamda Ollama açıkken:

```powershell
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m agent --verbose
```

Yukarıdaki, açıkça **farkların standart sapması** diyen demo sorgusunu girin; N=34 görünmeli. Sonra `çıkış` yazın. Yeni kurulum ve paket adımları [README](../README.md) içindedir. Bu aşamada temiz makinede yeniden kurulum yapılmadı; mevcut çalışan sanal ortam doğrulandı.

## 10. GitHub yükleme öncesi teslim kontrol listesi

- [x] Mevcut 109 test yeniden çalıştırıldı.
- [x] Gerçek Ollama + MCP testlerinin atlanmadığı kanıtlandı.
- [x] Tam demo sorgusu terminalde ve gerçek SDK çağrısında doğrulandı.
- [x] Negatif senaryolar ve başarısız semantik kontrol saklanmadan raporlandı.
- [x] Python/SDK/model yapılandırması ve kurulum komutları belgelendi.
- [x] Korunan uygulama ve test dosyalarının hash'leri değişmedi.
- [x] README, nihai rapor ve tekrar çalıştırılabilir kanıt toplama aracı hazırlandı.
- [ ] SD semantiği açığı giderilsin ve regresyon testi eklensin; ardından tam kabul tekrarlansın.
- [ ] Grup üyeleri eklenen dosyaları ve README içeriğini gözden geçirsin.
- [ ] Untracked Aşama 1/2 dosyaları dahil teslim kapsamı tek tek seçilsin; bu aşamada hiçbiri stage edilmedi.
- [ ] Yükleme öncesi aday dosya taraması tekrar çalıştırılsın; `.env`, anahtar, model, sanal ortam veya kişisel dosya eklenmesin.
- [ ] Önceden sağlanan JPG kanıtlarının paylaşım ve metadata uygunluğu grup tarafından kontrol edilsin.
- [ ] Commit/push kullanıcı/grup kararıyla yapılsın; bu çalışma commit/push içermez.

## 11. Diğer riskler ve eksikler

Doğal dil kontrolü bütün Türkçe ifadeleri kapsamaz; açık etiketlerle kullanım gerekebilir. `temperature=0` farklı model sürümlerinde mutlak determinizm sağlamaz. Transitif bağımlılıklar tamamen kilitli değildir. İlk model yüklemesi yavaş olabilir. Mevcut minimal N testi N−1 gücünü bağımsız doğrulamaz. Önceki raporlardaki 29.83 saniye gibi süreler önceki çalıştırmalara aittir; bu aşamanın gerçek süresi 36.49 saniyedir. 109 testin başarısı gizli testlerde belirli bir başarı oranını garanti etmez.
