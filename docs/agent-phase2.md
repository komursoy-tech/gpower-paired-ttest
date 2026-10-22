# Aşama 2 — Ollama doğal dil ajanı

## Mimari ve sınırlar

Türkçe kullanıcı girdisi → açık girdilerin doğrulanması → Ollama `qwen2.5:7b` tool calling → resmî Python MCP istemcisi → mevcut stdio FastMCP sunucusu → mevcut `core_engine.py` → doğrulanmış MCP sonucu → deterministik Türkçe yanıt.

Mevcut motor, SPEC, CLI, MCP sunucusu, Aşama 1 testleri ve README değiştirilmedi. Geliştirme `codex/mcp-server-phase1` dalında sürdürüldü; commit/push yapılmadı. Yeni bağımlılıklar `requirements-agent.txt` içindedir; temel ve MCP bağımlılık dosyaları korunur.

## Windows PowerShell kullanımı

Repository kökünde, mevcut Python 3.13.4 sanal ortamıyla:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-agent.txt
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
.\.venv\Scripts\python.exe -m agent
```

Ollama uygulaması çalışmalı ve model önceden indirilmiş olmalıdır. Model yoksa kullanıcıya `ollama pull` gerektiği bildirilir; ajan otomatik indirme yapmaz. Yerel çalışma API anahtarı gerektirmez. MCP sunucusunu ayrıca başlatmak gerekmez: ajan aynı sanal ortamın `sys.executable` yorumlayıcısıyla `python -m mcp_server` alt sürecini başlatır; repository yolu açıkça belirlenir.

Örnek soru:

> Öncesi ve sonrası tansiyon farkı 5 mmHg, standart sapması 10 mmHg. Alpha 0.05, güç %80 ve çift yönlü test için kaç hasta gerekir?

Gerçek hesaplamadan sonra yanıt N=34 tamamlanmış katılımcı/eşleşmiş çift, df=33, delta≈2.915476, kritik t≈2.034515, gerçek güç≈%80.7778 bilgilerini içerir. Kayıp katılımcı payı eklenmez.

Komutlar:

- `çıkış`, `cikis`, `exit`, `quit`: oturumu ve MCP alt sürecini kapatır.
- `yeni`, `reset`: bekleyen hesaplama girdilerini temizler.
- Ctrl+C veya stdin EOF: oturumu kapatır.
- `python -m agent --verbose`: istek kimliği, araç adı, gerçek argümanlar ve başarılı MCP sonucunu stderr'e kaydeder. Bu seçenek girilen çalışma istatistiklerini loga yazar; varsayılan modda bu ayrıntılı kayıt kapalıdır.

İsteğe bağlı ayarlar:

| Ortam değişkeni | Varsayılan | Açıklama |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Yerel model adı |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Tam HTTP/HTTPS adresi |
| `OLLAMA_TIMEOUT` | `180` | Model isteği için saniye; ilk yükleme daha yavaş olabilir |
| `MCP_TIMEOUT` | `30` | MCP başlatma/discovery ve araç çağrısı için saniye |

Zaman aşımı değerleri sonlu ve pozitif olmalıdır. Yerel API çağrılarında ortam proxy ayarları kullanılmaz. Modelin tools desteği yalnızca metadata üzerinden varsayılmaz: gerçek modelle native tool calling entegrasyon testleri vardır. Tools desteklemeyen modelin API hatası veya tool çağrısı üretmemesi açıkça raporlanır; bu aşamada sessiz JSON fallback uygulanmaz.

## Girdi güvenilirliği

Ollama araç seçimini ve argümanları üretir. Ajan, bunları discovery ile alınan gerçek MCP şemaları ve kullanıcının açıkça belirttiği değerlerle karşılaştırır. İzin verilen araçlar yalnızca şunlardır:

- `calculate_sample_size`
- `calculate_from_differences`
- `calculate_from_groups`

`agent/inputs.py` istatistik hesaplamaz; muhafazakâr bir dil/girdi kontrolü uygular. Tanınan etiketler arasında `dz`, `etki büyüklüğü`, `mean_diff`, `farkı`, `sd_diff`, `farkların standart sapması`, `mean1`, `mean2`, `sd1`, `sd2`, `öncesi/sonrası ortalama`, `öncesi/sonrası standart sapma`, `correlation`, `korelasyon`, `alpha`, `alfa`, `güç`, `target_power` vardır. Ondalık nokta/virgül ve açık yüzde ifadeleri desteklenir. Yüzde olasılığa dönüştürülür; dz veya örneklem sayısı hesaplanmaz.

Serbest Türkçe ifadelerin her olası biçiminin otomatik çözümlendiği iddia edilmez. Girdinin anlamı tanınmıyorsa alan adıyla netleştirme istenir. Belirsiz ve çelişkili ifadeler reddedilir; değerler tamamlanmaz. Semantik düzeltme sonrasında yalnızca fark ortalamasının bilinmesi, niteliksiz SD'nin fark SD'si sayılması için yeterli değildir. Açık `sd_diff`/“farkların standart sapması” kabul edilir. “Her bir ölçümün standart sapması” yalnızca `sd1`/`sd2` sağlar; eksik ortalamalar ve korelasyon istenir. Önceden çalışan iyelikli “farkı ..., standart sapması ...” biçimi ve açık fark SD'si sorusuna verilen doğrudan yanıt dar bağlamda korunur. SD türü sorulmuşsa tek sayı bu türü netleştirmiş sayılmaz. Birden fazla alan eksikse alan adlarıyla yanıt verilmelidir.

Yön, alpha, güç veya korelasyon için varsayılan yoktur. Örneğin yön eksikse kullanıcıya tek/çift yön sorulur. Başarılı hesaplamadan sonra bağlam sıfırlanır; sonraki soruya eski parametreler veya eski N taşınmaz. Eksik bilgileri tamamlama sırasında bağlam tutulur. Girdi uzunluğu ve konuşma turu sınırları vardır.

Her kullanıcı turunda en fazla bir model isteği ve bir hesaplama aracı çağrısı yapılır. Çoklu araç çağrısı veya bilinmeyen araç adı reddedilir. Otomatik, sınırsız tool calling/retry döngüsü yoktur. Eksik girdide model veya hesaplama çağrısına gerek olmadan sabit, güvenli netleştirme sorusu gösterilir.

Modelin serbest metni kullanıcıya hesaplama cevabı olarak gösterilmez. Başarılı MCP cevabından önce N veya diğer hesaplanan değerler sunulmaz. İstemci `isError`, discovery çıktı şeması, beş zorunlu alan, sonluluk, N/df türleri ve temel tutarlılığı kontrol eder. Sayısal yanıt `agent/presentation.py` tarafından yalnızca doğrulanan gerçek cevaptan oluşturulur. İkinci bir model üretimi gerekmez; sonuçlar modelin yeniden yazımında değişemez.

Şema, bool/string/null/nonfinite ve ek/eksik alan kontrolleri istemcide de uygulanır. İstatistiksel hesaplama ve alanlar arası matematiksel kontroller mevcut sunucu/motorda kalır. Motor hatası başarılı sonuca dönüştürülmez. Model/API bağlantı, model eksikliği, zaman aşımı ve MCP hataları görünürdür.

## Dosyalar

| Dosya | Sorumluluk |
|---|---|
| `agent/__main__.py` | Türkçe terminal, çıkış ve hata gösterimi |
| `agent/config.py` | Ortam değişkenleri |
| `agent/errors.py` | Kullanıcıya gösterilen hatalar |
| `agent/ollama_client.py` | Resmî `ollama.AsyncClient`, bağlantı/model kontrolü, native tool calling |
| `agent/mcp_client.py` | Resmî `ClientSession`, stdio, discovery, şema dönüşümü ve doğrulama |
| `agent/inputs.py` | Açık kullanıcı girdisi kontrolü ve eksik alan soruları |
| `agent/orchestrator.py` | Sınırlı akış, argüman eşleştirme, gerçek çağrı ve işlem kaydı |
| `agent/presentation.py` | Deterministik Türkçe sonuç |
| `requirements-agent.txt` | Ajan bağımlılıkları |
| `tests/test_agent.py` | Güvenilirlik testleri ve gerçek MCP ile mock-model testleri |
| `tests/test_agent_live.py` | Gerçek Ollama + gerçek MCP ve terminal testleri |

## Testlerin çalıştırılması

```powershell
# Mevcut testler + ajan birim/stdio testleri; canlı model testleri açıkça atlanır.
.\.venv\Scripts\python.exe -m pytest -q

# Gerçek yerel model testi; servis/model yoksa test başarısız olur.
$env:RUN_OLLAMA_TESTS = '1'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
.\.venv\Scripts\python.exe -m pytest tests/test_agent_live.py -v

# Tam kabul: canlı testler dahil bütün paket.
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
Remove-Item Env:RUN_OLLAMA_TESTS
```

Mock testleri gerçek model başarısının kanıtı sayılmaz. `RUN_OLLAMA_TESTS=1` ayarı model testlerini etkinleştirir; çalışmayan servis/model yüzünden sessiz skip yapılmaz. Gerçek testlerde modelin gerçek tool çağrısı, doğru adı ve bütün argümanları, gerçek MCP cevabındaki N=34 ve terminalin çıkış komutuyla kapanışı doğrulanır.

## Doğrulama ortamı

Python 3.13.4; MCP SDK 1.30.0; Ollama Python istemcisi 0.6.3; Pydantic 2.14.1; pytest 9.1.1. Yerel `qwen2.5:7b` model kimliği: `845dbda0ea48`. İlk kontrol sırasında Aşama 1'in 61 testi yeniden başarılı oldu. İlk dört gerçek model senaryosu 168.18 saniyede geçti; bu süre ilk model yüklemesini de içerir.

Aşama 2'nin 22 Ekim 2026 tarihli kabul çalıştırması: **109 başarılı, 0 başarısız, 0 atlanan test; 29.83 saniye**. Dağılım: 26 mevcut motor/CLI/doğrulama testi + 35 Aşama 1 MCP testi + 43 ajan testi + 5 gerçek Ollama/MCP/terminal testi. Bu tarihsel sonuçtan sonra semantik düzeltme için 26 test eklendi: güncel sonuç **135 başarılı, 0 başarısız, 0 atlanan; 40.16 saniye**. Canlı testler kapalı normal çalıştırmada artık yedi test açık skip olur. Güncel kanıtlar ve kök neden [nihai rapordadır](final-integration-report.md).

Resmî kaynaklar: [Ollama Python istemcisi](https://github.com/ollama/ollama-python), [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling).
