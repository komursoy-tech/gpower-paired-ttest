# G*Power Paired t-Test — MCP + Ollama Entegrasyonu: Mimari Plan

**Tarih:** 22 Ekim 2026  
**Durum:** Yalnızca planlama; uygulama için açık kullanıcı onayı bekleniyor.

**Öneri:** Mevcut hesaplama motorunu değiştirmeden üç araç sunan bir MCP sunucusu ve bu sunucuya gerçekten bağlanan, Ollama destekli bir terminal ajanı geliştirmek.

Bu plan hazırlanırken yalnızca inceleme yapıldı; uygulama kodu yazılmadı, paket yüklenmedi ve mevcut proje dosyaları değiştirilmedi. Orijinal G*Power uygulaması veya iç yapısı incelenmedi. Bu Markdown dosyası, kullanıcının ayrıca verdiği planı kaydetme talebiyle oluşturulmuştur.

## 1. Mevcut repository analizi

Repository: https://github.com/komursoy-tech/gpower-paired-ttest

Analiz, yerel checkout’taki `b3e50b2` commit’ine dayanıyor. İnceleme sırasında aktif dal `main`, çalışma ağacı temizdi. Git remote adresi verilen repository ile eşleşiyor; GitHub sayfası tarayıcı üzerinden alınamadığı için uzak dalın güncelliği doğrulanmadı.

İncelenen temel dosyalar:

- [SPEC.md](SPEC.md)
- [core_engine.py](core_engine.py)
- [cli.py](cli.py)
- [requirements.txt](requirements.txt)
- [tests/](tests/)
- [validation_report.md](validation_report.md)

### Motorun kullanılabilir fonksiyonları

| Fonksiyon | Girdiler | Çıktı |
|---|---|---|
| `power_matched_pairs` | `effect_size_dz`, `alpha`, `target_power`, `tails` | Beş alanlı sonuç sözlüğü |
| `calculate_dz_from_differences` | `mean_diff`, `sd_diff` | `float` etki büyüklüğü |
| `calculate_dz_from_groups` | `mean1`, `mean2`, `sd1`, `sd2`, `correlation` | `float` etki büyüklüğü |

`power_matched_pairs` sonucu: `sample_size`, `df`, `delta`, `critical_t`, `actual_power`.

Motor üstel arama ve ikili aramayla minimal tam sayı N’i buluyor; üst sınır 100.000. Merkezi olmayan t CDF’i sonlu değer üretmezse sayısal integrasyon yedeği kullanılıyor. MCP katmanı bu işlemlerin hiçbirini yeniden uygulamamalı.

### Validasyon sözleşmesi

- Sayısal değerler `numbers.Real` olmalı; `bool`, metin ve `Decimal` reddediliyor.
- `None`, `NaN` ve sonsuz değerler geçersiz.
- `0 < alpha < 1`, `0 < target_power < 1`, `effect_size_dz > 0`.
- `tails`: yalnızca `one-tailed` veya `two-tailed`.
- Fark ortalaması negatif olabilir; sıfır olamaz.
- Fark standart sapmasının sıfır olması `ZeroDivisionError`, negatif olması `ValueError`.
- Grup standart sapmaları pozitif, korelasyon `[-1, 1]` aralığında olmalı.
- Grup fark varyansındaki göreli eşik kontrolü motorda kalmalı.
- Hata türleri, mesajları ve parametre kontrol sırası korunmalı.

### Entegrasyon açısından iki ayrıntı

1. Motor ve CLI’de `alpha=0.05`, `target_power=0.80`, `tails="two-tailed"` varsayılanları var. Ancak SPEC bunları açıkça varsayılan ilan etmiyor; örnek değerler veriyor. Kullanıcının kuralı gereği ajan eksik değerleri şimdilik sormalı.
2. Determine fonksiyonları `alpha`, güç ve yön parametrelerini almıyor. Dolayısıyla birleşik MCP araçlarında önce Determine fonksiyonu, ardından güç fonksiyonu çağrılınca hata önceliği bu çağrı sırasını izler. Bütün parametreler için SPEC tablosundaki tek bir küresel sırayı garanti ettiğimiz iddia edilmemeli.

Bu durumlar motoru değiştirmeyi gerektiren ciddi bir engel oluşturmuyor.

### Mevcut test mimarisi

Kaynaklarda toplam 26 pytest vakası bulunuyor:

| Dosya | Kapsam |
|---|---|
| `test_core.py` | Determine hesapları, bazı hatalı girdiler |
| `test_cli.py` | Üç giriş modu, eksik/geçersiz argümanlar |
| `test_validation.py` | SPEC’teki 11 temel doğrulama vektörü |

Dikkat edilmesi gereken boşluklar:

- Minimal N kontrolü aynı fonksiyonu aynı hedefle tekrar çağırıyor; `N−1` için gücün yetersizliğini bağımsız doğrulamıyor.
- SPEC’in tüm negatif vektörleri pytest kapsamına alınmamış.
- Ondalıklı sonuçlarda `pytest.approx(..., abs=1e-5)` kullanılıyor; yalnızca mutlak tolerans isteniyorsa yeni testlerde `rel=0` belirtilmeli.
- Bazı ek kontroller motorun `__main__` bölümünde; normal pytest çalıştırması bunları çalıştırmıyor.

Doğrulama raporundaki **26/26 başarılı** bilgisi önceki çalıştırmaya ait. İnceleme oturumunda bağımlılıklar bulunmadığından testler yeniden çalıştırılmadı.

**Clean-room sınırı:** SPEC, mevcut bağımsız Python motoru ve repository’deki doğrulama kayıtları kullanılacak. Orijinal uygulama, binary, decompile çıktısı veya iç algoritmalar araştırılmayacak.

## 2. Önerilen MCP mimarisi

Akış:

**MCP istemcisi → stdio → MCP sunucusu → mevcut motor → yapılandırılmış sonuç**

Yerel kullanım için stdio uygun: HTTP sunucusu, port veya kimlik doğrulama kurulumu gerektirmeden istemci alt süreç başlatabilir.

### SDK seçimi

Resmî `mcp` Python SDK’sı kullanılmalı. Belgelerde v1’deki `FastMCP` yaklaşımı ile v2’deki `MCPServer` API’si ayrılıyor. Bu nedenle uygulama başlangıcında yayımlanmış kararlı sürüm doğrulanıp sunucu ve istemci aynı sürüme sabitlenmeli. FastMCP API’si tercih edilirse v1 belgeleri ve uyumlu sürüm birlikte seçilmeli; sürüm aileleri karıştırılmamalı.

Kaynaklar: [Resmî SDK](https://github.com/modelcontextprotocol/python-sdk), [geçiş belgesi](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md).

### Araçlar

| Araç | Açıklama | Motor çağrıları |
|---|---|---|
| `calculate_sample_size` | Pozitif dz üzerinden eşleştirilmiş t-testi örneklem büyüklüğü | `power_matched_pairs` |
| `calculate_from_differences` | Eşleşmiş farkların ortalaması ve standart sapması üzerinden hesaplama | `calculate_dz_from_differences` → `power_matched_pairs` |
| `calculate_from_groups` | Aynı bireylerin iki ölçümünün özet istatistikleri ve korelasyonu üzerinden hesaplama | `calculate_dz_from_groups` → `power_matched_pairs` |

Grup aracı açıklamasında bunun bağımsız iki grup testi olmadığı açıkça yazılmalı.

### Input schema

Başlangıçta bütün alanlar zorunlu olmalı. Her araç yalnızca kendi giriş moduna ait alanları ve ortak `alpha`, `target_power`, `tails` alanlarını alır.

| Alan | Şema |
|---|---|
| `effect_size_dz` | JSON number, `> 0` |
| `mean_diff` | JSON number, sıfır dışı |
| `sd_diff` | JSON number, `> 0` |
| `mean1`, `mean2` | JSON number |
| `sd1`, `sd2` | JSON number, `> 0` |
| `correlation` | JSON number, `-1 ≤ r ≤ 1` |
| `alpha`, `target_power` | JSON number, açık aralık `(0,1)` |
| `tails` | İki değerli enum: `one-tailed`, `two-tailed` |

Bilinmeyen alanlar reddedilmeli. Sayısal metinler ve boolean değerler otomatik sayıya çevrilmemeli. JSON number hem tam sayıyı hem ondalığı kapsamalı.

Şema, tek alanlı kısıtları tanımlar; alanlar arası kurallar ve matematiksel validasyon motorun sorumluluğunda kalır. JSON taşımacılığında Python’a özgü `Fraction` veya NumPy türleri beklenmez.

### Output schema

Başarılı sonuçta:

| Alan | İçerik |
|---|---|
| `schema_version` | Sözleşme sürümü |
| `tool_name` | Çalışan araç |
| `inputs` | Gerçekte kullanılan girdiler |
| `effect_size_dz` | Girilen veya motordan türetilen dz |
| `result` | Motorun beş alanlı sonucu |

Bütün sayısal çıktılar sonlu olmalı. N, tamamlanmış **eşleşmiş çift/katılımcı sayısıdır**; toplam ölçüm sayısı değildir. Kayıp katılımcı payı otomatik eklenmemeli.

### Hata yönetimi

- Şema hatası: eksik alan, yanlış tür, bilinmeyen alan.
- Motor hatası: özgün istisna türü ve mesajı korunarak MCP tool hatasına çevrilir.
- Çalışma hatası: örneklem sınırı veya güç hesaplama başarısızlığı.
- Beklenmeyen hata: stderr’e ayrıntılı kayıt; kullanıcıya anlaşılır hata.

Başarısız çağrı `isError=true` olarak taşınmalı ve başarılı sonuç şemasına dönüştürülmemeli. Seçilen SDK’nın otomatik şema hataları ile motor mesajlarının farklı olabileceği belgelenmeli.

### İstemci-sunucu yaşam döngüsü

Ajan, kendi Python yorumlayıcısıyla sunucuyu modül olarak başlatır; çalışma dizinini açıkça belirler; SDK sürümünün gerektirdiği bağlantı/başlatma işlemlerini tamamlar; araçları keşfeder; çağrıları yapar; çıkışta bağlantıyı ve alt süreci kapatır. stdout yalnızca MCP trafiğine, stderr loglara ayrılır.

## 3. Önerilen Ollama ajan mimarisi

**Türkçe sorgu → Ollama → doğrulanmış araç isteği → MCP istemcisi → MCP sunucusu → motor → Türkçe açıklama**

Ollama doğrudan MCP istemcisi değildir. Aradaki Python ajanı bu köprüyü kurar:

1. MCP üzerinden araçları keşfeder.
2. Araç adlarını, açıklamalarını ve input şemalarını Ollama tool biçimine dönüştürür.
3. Kullanıcı mesajını modele gönderir.
4. Modelin önerdiği araç ve argümanları doğrular.
5. Yalnızca keşfedilen üç araca izin verir.
6. Gerçek MCP çağrısını gerçekleştirir.
7. Başarılı cevabı tool mesajı olarak modele iletir.
8. Kullanıcıya sunulan sayısal sonuçları doğrulanmış MCP cevabından yerleştirir.

Ollama’nın resmî akışında da araç çağrısını uygulama yürütür ve sonucu modele geri verir. Kaynak: [Tool calling belgesi](https://docs.ollama.com/capabilities/tool-calling).

### Sonuç uydurmayı engelleme

Yalnızca prompt talimatına güvenilmemeli:

- Başarılı MCP cevabı yoksa sayısal hesaplama sonucu gösterilmez.
- Modelin yazdığı N, uygulamanın sonuç kaynağı olarak kullanılmaz.
- Sayısal sonuç bölümü deterministik Türkçe şablonla üretilir.
- Model açıklaması kullanılacaksa sayısal ve yöntemsel iddiaları kontrol edilir; kontrol başarısızsa şablon kullanılır.
- Her işlemde istek kimliği, araç adı, doğrulanmış argümanlar, gerçek cevap ve hata durumu ilişkilendirilir.

### Örnek sorgunun işlenmesi

> Öncesi ve sonrası tansiyon farkı 5 mmHg, standart sapması 10 mmHg olan bir araştırmada alpha 0.05 ve %80 güç için kaç hasta gerekir?

Bu örnekte `tails` belirtilmiyor. SPEC açık varsayılan tanımlamadığı için ajan önce “Tek yönlü mü, çift yönlü mü?” diye sormalı. Çift yönlü yanıtından sonra `mean_diff=5`, `sd_diff=10`, `alpha=0.05`, `target_power=0.80`, `tails="two-tailed"` ile `calculate_from_differences` çağrılır ve SPEC’e göre N=34 beklenir. Tek yönlü durumda N=27’dir.

Başarılı çift yönlü yanıt örneği:

> Verdiğiniz fark ortalaması 5 ve farkların standart sapması 10 için etki büyüklüğü dz=0,5. Çift yönlü testte, α=0,05 ve hedef güç %80 için en az 34 tamamlanmış katılımcı çifti gerekir. Ulaşılan güç yaklaşık %80,78’dir.

Bu metin ancak gerçek MCP cevabından sonra üretilir.

### Belirsizlik politikası

- “Standart sapma 10” ifadesinin farklara mı, tek ölçüme mi ait olduğu belirsizse sorulur.
- Korelasyon eksikse tahmin edilmez.
- `%80` güç, `0.80` olarak yorumlanabilir; bu dönüşüm kullanıcıya gösterilir.
- Çelişkili giriş modlarında kullanıcıdan netleştirme istenir.
- Eksik parametreler çok turlu konuşmada tamamlanır.

### Model seçimi ve yapılandırma

Model adı `OLLAMA_MODEL` üzerinden yapılandırılmalı; başlangıçta belirtilmesi zorunlu olabilir. Yerel adres varsayılanı `http://127.0.0.1:11434` olur. Yerel çalışma için API anahtarı gerekmez.

Donanım doğrulamasından sonra `qwen3:4b` ve `qwen3:8b` aday olarak denenebilir. Ollama kütüphanesinde Qwen3 tools desteğiyle listeleniyor; Türkçe doğruluk ve araç seçimi ayrıca ölçülmeli. Model dosya boyutu, çalışma zamanı RAM/VRAM ihtiyacıyla aynı değildir. Kaynak: [Model bilgisi](https://ollama.com/library/qwen3).

**Tool calling yoksa:** JSON Schema ile yalnızca araç adı, argümanlar veya eksik alanları çıkaran alternatif mod değerlendirilir. Doğrulanan istek yine gerçek MCP üzerinden yürütülür. Şemaya uygun çıktı da güvenilir değilse model reddedilir ve başka model seçilir. Kaynak: [Structured outputs belgesi](https://docs.ollama.com/capabilities/structured-outputs).

## 4. Kullanılacak kütüphaneler ve gerekçeleri

| Kütüphane | Amaç |
|---|---|
| `mcp` | Resmî MCP sunucusu, istemcisi ve stdio taşımacılığı |
| `ollama` | Yerel Ollama API istemcisi |
| `pydantic` | Katı veri sözleşmeleri ve model çıktısı doğrulama |
| `pytest` | Mevcut ve yeni testler |
| `anyio` | SDK ile uyumlu asenkron entegrasyon testleri |
| Mevcut NumPy/SciPy | Yalnızca mevcut hesaplama motoru |

Standart kütüphaneden `logging`, `pathlib`, `sys`, `os` ve gerektiğinde `asyncio` yeterli olur. İlk sürüm için LangChain veya ek ajan çatısı gerekli görünmüyor.

Mevcut `requirements.txt` korunabilir. Entegrasyon ve test bağımlılıkları ayrı dosyalarda tutulmalı; çalışan kombinasyon doğrulandıktan sonra tam sürümler kilitlenmeli.

## 5. Oluşturulacak dosyalar

Aşağıdaki yapı yalnızca öneridir; bu plan dosyası dışında henüz oluşturulmadı.

| Önerilen dosyalar | Sorumluluk |
|---|---|
| `mcp_server/__init__.py`, `__main__.py` | Paket ve stdio başlangıcı |
| `mcp_server/server.py` | Üç araç ve motor adaptörleri |
| `mcp_server/schemas.py`, `errors.py` | Veri sözleşmeleri, hata dönüşümü |
| `agent/__init__.py`, `__main__.py` | Türkçe terminal arayüzü |
| `agent/config.py` | Model, adres, zaman aşımı ayarları |
| `agent/mcp_client.py` | Süreç, bağlantı, discovery, çağrı |
| `agent/ollama_client.py` | Yerel model iletişimi |
| `agent/orchestrator.py` | Araç seçimi ve konuşma akışı |
| `agent/presentation.py` | Doğrulanmış Türkçe sonuç |
| `tests/mcp/` | Sunucu ve gerçek stdio testleri |
| `tests/agent/` | Mock modelle ajan testleri |
| `tests/integration/` | Gerçek Ollama ve MCP testleri |
| `docs/mcp.md`, `docs/agent.md` | Mimari ve kullanım |
| `docs/windows-setup.md`, `docs/acceptance.md` | Kurulum ve kabul kanıtları |
| `requirements-integration.txt`, `requirements-dev.txt` | Ayrı bağımlılık kümeleri |
| `pytest.ini` | Entegrasyon test işaretleri |
| `README.md` | Onaydan sonra hızlı başlangıç ve doküman bağlantıları |

`core_engine.py`, mevcut CLI ve test dosyaları korunur.

## 6. Geliştirme aşamaları ve sıralaması

1. **Ortamı doğrulama:** Python yorumlayıcısı, bağımlılıklar, Ollama servisi ve donanım.
2. **Mevcut tabanı doğrulama:** 26 testin gerçek sonuçlarını kaydetme.
3. **Sözleşmeleri netleştirme:** SDK sürümü, zorunlu alanlar, hata ve çıktı biçimi.
4. **MCP sunucusu:** Üç ince adaptör ve gerçek stdio istemci testleri.
5. **Ollama bağlantısı:** Model yapılandırması ve araç şeması dönüşümü.
6. **Ajan:** Eksik bilgi diyaloğu, doğrulama, gerçek çağrı ve sonuç sunumu.
7. **Uçtan uca kabul:** Türkçe sorgular, N=34, hata ve kesinti senaryoları.
8. **Dokümantasyon ve teslim:** PowerShell kurulum adımları, sürümler, kanıtlar, README.

### Git ve grup çalışması stratejisi

Onaydan sonra `codex/mcp-ollama-integration` dalı; MCP, ajan ve dokümantasyon değişiklikleri anlaşılır ayrı commit’ler. README, bağımlılık dosyaları ve pytest ayarları ortak çakışma noktaları olduğundan grup içinde dosya sahipliği belirlenmeli. Merge öncesi motorun kamuya açık imzaları yeniden kontrol edilmeli ve bütün testler çalıştırılmalı.

## 7. Test ve kabul kriterleri

| Katman | Kabul kriteri |
|---|---|
| Mevcut proje | Mevcut 26 test başarılı |
| Sunucu başlangıcı | stdio süreci açılır ve düzgün kapanır |
| Discovery | Tam olarak üç beklenen araç, input ve output şemaları |
| Gerçek çağrı | Üç araç gerçek alt süreç üzerinden cevap verir |
| Referans sonuç | Doğrudan dz, farklar ve grup örneklerinin her biri N=34 |
| Sayısal sonuçlar | N/df tam eşit; diğer alanlarda yalnızca `1e-5` mutlak tolerans |
| Validasyon | Metin, bool, null, eksik alan, ek alan ve sınır değerleri reddedilir |
| Motor kullanımı | Birim testlerinde spy ile doğru fonksiyon ve argümanlar doğrulanır |
| Mock ajan | Sahte Ollama yanıtı gerçek MCP çağrısını tetikler |
| Gerçek Ollama | Türkçe sorgu doğru aracı ve değerleri seçer |
| Eksik bilgi | Özellikle yön ve korelasyon eksikse soru sorulur |
| Başarısızlık | MCP/Ollama hatasında uydurma N gösterilmez |
| Kaynak yönetimi | Zaman aşımı ve iptal sonrasında yetim sunucu kalmaz |

**Mock ve gerçek testler ayrılmalı.** Gerçek Ollama testleri ayrı işaretle açıkça çalıştırılır. Normal testte bunların atlanması raporlanır; gerçek entegrasyon kabul çalıştırmasında servis/model eksikliği başarı sayılmaz. Başarısız testler gizlenmez.

Gerçek çağrı kanıtı, yalnızca modelin “aracı kullandım” demesi olamaz. İstemci isteği, sunucu işlem kaydı ve eşleşen MCP cevabı birlikte doğrulanmalı.

`NaN` ve sonsuz değerler standart JSON’da taşınamayacağından bunlar Python adaptör testlerinde; bozuk JSON ise ayrı protokol testlerinde ele alınmalı.

## 8. Teknik riskler ve çözümleri

| Risk | Çözüm |
|---|---|
| MCP sürüm/API farkları | Tek sürüm ailesi, kilitli sürümler, o sürümün belgeleri |
| Şemanın `"0.5"` veya `true` değerini sayıya çevirmesi | Katı tip doğrulaması ve negatif testler |
| Birleşik araçlarda hata önceliği farkı | Çağrı sırasını belgeleme; küresel SPEC sırası iddia etmeme |
| Modelin sayı uydurması | MCP cevabı zorunluluğu ve deterministik sonuç sunumu |
| Türkçe belirsizlik | Alanların anlamını netleştiren çok turlu diyalog |
| Windows yolunda boşluk/Türkçe karakter | Argüman dizileri, açık çalışma dizini, `sys.executable` |
| stdout’a log yazılması | Logların stderr’e yönlendirilmesi |
| Modelin yavaşlığı | Donanıma göre model seçimi, ayrı model/MCP zaman aşımı |
| NumPy/SciPy sürüm farkları | Desteklenen Python ortamı ve tüm SPEC regresyonları |
| Klinik örneğin yanlış yorumlanması | Fark SD’si, eşleşme ve tamamlanmış katılımcı sayısının açıklanması |

## 9. Kurulum için gereken ortam kontrolleri

İnceleme oturumunda gözlenen durum:

| Kontrol | Bulgular |
|---|---|
| Python | Varsayılan `C:\Python315\python.exe`, sürüm 3.15.0 |
| Python launcher | Yalnızca 3.15 listelendi; konum uyarısı verdi |
| Paketler | Bu yorumlayıcıda NumPy, SciPy, pytest, mcp, ollama, pydantic bulunamadı |
| Ollama CLI | Kurulu; istemci sürümü 0.33.3 |
| Ollama servisi | Bağlantı doğrulanamadı |
| Yerel modeller | Listelenemedi |
| GPU/RAM/VRAM | Henüz doğrulanmadı |

Ollama bağlantı denemesi soket erişim izni hatası verdi. Bu, servisin kesin olarak kapalı olduğunu kanıtlamıyor; oturum kısıtlaması da etkili olabilir. Doğrulama raporundaki Python 3.14.3 ile mevcut varsayılan 3.15.0 da farklı.

**Öncelik:** Bilimsel paketler ve seçilen SDK için Windows uyumluluğu doğrulanmış bir Python sürümüyle proje sanal ortamı kullanmak. Python 3.12/3.13 aday olabilir; mevcut 3.15 ortamının uyumluluğu varsayılmamalı.

Onaydan sonra kullanıcı PowerShell’inde yapılacak salt okunur kontroller:

- `py -0p`
- `python --version`
- `python -m pip --version`
- `ollama --version`
- `ollama list`
- `Invoke-RestMethod http://127.0.0.1:11434/api/tags`
- RAM/GPU bilgileri; NVIDIA varsa `nvidia-smi`.

Kurulum sırası daha sonra: doğrulanmış Python ile `.venv` oluşturma → temel ve entegrasyon bağımlılıklarını yükleme → seçilen modeli indirme → MCP testi → ajan testi. Aktivasyon zorunlu tutulmayıp doğrudan `.\.venv\Scripts\python.exe` kullanılması PowerShell execution policy sorunlarını azaltır. Kesin paket sürümleri doğrulanmadan kurulum komutları sabitlenmemeli.

## 10. Uygulamaya geçmeden önce cevaplanması gereken sorular

1. **Eksik yön için soru sorulmasını kabul ediyor musunuz?** Mevcut SPEC’e göre öneri bu. Örnek sorgunun doğrudan N=34 vermesi isteniyorsa çift yönlü varsayılanı SPEC’te açıkça tanımlamak için grup kararı gerekir.
2. **RAM, GPU ve varsa VRAM kapasiteniz nedir?** Model boyutu buna göre seçilmeli.
3. **Proje için ayrı, uyumlu bir Python ortamı kullanılabilir mi?** Mevcut 3.15 ortamında gerekli paketler yok.
4. **Hocanız belirli bir MCP istemcisiyle gösterim bekliyor mu?** Öneri, bağımsız stdio sunucusu ve ona bağlanan terminal ajanı.
5. **Grup içinde README, bağımlılık dosyaları ve SPEC’in sorumlusu kim?** Merge çakışmaları ve varsayılan kararı buna göre koordine edilmeli.

PLAN HAZIR. UYGULAMAYA GEÇMEK İÇİN ONAY BEKLİYORUM.
