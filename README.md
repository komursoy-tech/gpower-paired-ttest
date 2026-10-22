# G*Power Paired t-Test — Python, MCP ve Ollama

Eşleştirilmiş iki ortalama t-testi için a priori örneklem büyüklüğü analizi. Python motoru, G*Power'ın ilgili modülünün davranışını [SPEC.md](SPEC.md) sözleşmesine göre bağımsız olarak uygular. MCP sunucusu motoru araçlar olarak sunar; yerel Ollama ajanı Türkçe sorguları bu araçlara bağlar.

**Doğrulama durumu — 22 Ekim 2026:** Tek ölçüm SD'sinin fark SD'si sayılması hatası yeniden üretildi ve düzeltildi. Mevcut 109 test ile 26 yeni regresyonun tamamı geçti: **135 başarılı, 0 başarısız, 0 atlanan**. Yedi gerçek Ollama + MCP testi ve dokuz negatif kontrol başarılı. [Nihai rapor, kök neden ve önce/sonra kanıtları](docs/final-integration-report.md).

## Clean-room yaklaşımı ve motor

Hesaplama sözleşmesi SPEC'tir. Orijinal G*Power kaynak kodu, binary iç yapısı veya decompile çıktısı entegrasyon geliştirmesinde kullanılmaz; bu repository'ye program dosyası eklenmez. Kullanıcı tarafından daha önce sağlanan doğrulama ekran görüntülerinin kapsamı [validation_report.md](validation_report.md) içinde açıklanır. Bu doğrulama aşamasında orijinal uygulama açılmadı veya incelenmedi.

`core_engine.py` şu fonksiyonları sağlar:

- `power_matched_pairs`: dz, alpha, hedef güç ve yön üzerinden gereken N'i bulur.
- `calculate_dz_from_differences`: fark ortalaması ve farkların standart sapmasından dz türetir.
- `calculate_dz_from_groups`: aynı kişilerin iki ölçümünün ortalamaları, SD'leri ve korelasyonundan dz türetir.

Motor merkezi olmayan t dağılımını, gerektiğinde sayısal integrasyon yedeğini ve minimal tam sayı N aramasını kullanır. Üst sınır 100.000'dir. Çıktılar `sample_size`, `df`, `delta`, `critical_t`, `actual_power` alanlarıdır. N, tamamlanmış eşleşmiş çift/katılımcı sayısıdır; toplam ölçüm sayısı veya kayıp payı eklenmiş örneklem değildir.

## Mimari

```text
Türkçe kullanıcı girdisi
  → açık girdilerin kontrolü
  → Ollama qwen2.5:7b (araç seçimi ve argümanlar)
  → Python MCP istemcisi (discovery, şema ve argüman kontrolü)
  → stdio FastMCP sunucusu
  → mevcut core_engine.py
  → doğrulanmış MCP sonucu
  → deterministik Türkçe yanıt
```

| MCP aracı | Özel parametreler |
|---|---|
| `calculate_sample_size` | `effect_size_dz` |
| `calculate_from_differences` | `mean_diff`, `sd_diff` |
| `calculate_from_groups` | `mean1`, `mean2`, `sd1`, `sd2`, `correlation` |

Ortak ve zorunlu parametreler: `alpha`, `target_power`, `tails`. Yön `one-tailed` veya `two-tailed` olmalıdır. Korelasyon dahil eksik parametrelere varsayılan atanmaz. Bool, sayısal metin, null, sonlu olmayan değerler ve ek/eksik alanlar reddedilir. Matematik sunucu/ajan katmanında yeniden uygulanmaz.

Sunucu resmî MCP SDK 1.30.0'ın `FastMCP` API'sini kullanır. Sunucu stdout'u yalnızca protokol mesajları, stderr'i loglar içindir. Ajan resmî Ollama ve MCP istemcilerini kullanır; MCP alt sürecini kendisi başlatır ve kapatır. Modelin serbest metni hesaplama sonucu olarak gösterilmez. Başarılı ve doğrulanmış MCP cevabı olmadan sayısal hesaplama yanıtı verilmez. Her turda en fazla bir model isteği ve bir araç çağrısı vardır.

## Windows PowerShell kurulumu

Doğrulanan ortam: Python 3.13.4, Ollama CLI 0.33.3, `qwen2.5:7b`. Model dosyası yerel listede yaklaşık 4.7 GB'dır; bu değer RAM/VRAM gereksinimi değildir. Gerçek donanım ve ilk yükleme süresi değişebilir. Yerel kullanım API anahtarı gerektirmez.

```powershell
git clone https://github.com/komursoy-tech/gpower-paired-ttest.git
Set-Location gpower-paired-ttest
py -0p
# Python 3.13 launcher'da kayıtlıysa; mevcut .venv varsa yeniden oluşturmayın.
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-agent.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
```

Python 3.13 launcher'da listelenmiyorsa kurulu 3.13 yorumlayıcısını seçip `-m venv .venv` çalıştırın. Varsayılan `python` sürümünün uygun olduğunu varsaymayın. Sanal ortamı aktive etmek zorunlu değildir.

Ollama'yı başlatın; aşağıdaki indirme adımı model zaten kuruluysa gerekmez:

```powershell
ollama --version
ollama list
ollama pull qwen2.5:7b
$env:OLLAMA_MODEL = 'qwen2.5:7b'
$env:OLLAMA_HOST = 'http://127.0.0.1:11434'
$env:PYTHONIOENCODING = 'utf-8'
.\.venv\Scripts\python.exe -m agent
```

Çıkış: `çıkış` veya `exit`. Bekleyen girdileri temizleme: `yeni`. Eksik alanlar sonraki mesajda tamamlanabilir. Gerekirse `OLLAMA_TIMEOUT` (varsayılan 180 saniye) ve `MCP_TIMEOUT` (30 saniye) ayarlanabilir.

## Örnek sorgular ve komutlar

> Öncesi ve sonrası sistolik tansiyon farkı 5 mmHg, farkların standart sapması 10 mmHg. Alfa 0.05, güç %80, çift yönlü test için kaç hasta gerekir?

Doğrulanmış demo: `calculate_from_differences`, N=34, df=33, ulaşılan güç yaklaşık %80.7778.

> Etki büyüklüğü dz=0.5, alpha=0.05, güç %80, çift yönlü eşleştirilmiş test için kaç katılımcı gerekir?

> Aynı kişilerin öncesi ortalama 140, sonrası ortalama 135, öncesi standart sapma 10, sonrası standart sapma 10. Korelasyon 0.5, alpha 0.05, güç %80, çift yönlü test için kaç kişi gerekir?

Doğrudan mevcut CLI veya ayrı MCP sunucusu:

```powershell
.\.venv\Scripts\python.exe cli.py --effect-size 0.5 --alpha 0.05 --power 0.80 --tails two-tailed
.\.venv\Scripts\python.exe -m mcp_server
```

MCP sunucusu terminal sohbeti değildir; MCP istemcisinden JSON-RPC bekler. Ajan kullanırken ayrıca başlatmayın. `--verbose` ajan seçeneği stderr'e gerçek araç argümanlarını ve cevaplarını yazar; yalnızca paylaşılabilir örnek verilerle demo kaydı alın.

## Testler ve gerçek sonuçlar

```powershell
# Birim ve MCP testleri; 7 canlı model testi bilinçli skip olur.
.\.venv\Scripts\python.exe -m pytest -q

# Teslim kabulü: gerçek model testleri dahil bütün paket.
$env:RUN_OLLAMA_TESTS = '1'
$env:OLLAMA_MODEL = 'qwen2.5:7b'
.\.venv\Scripts\python.exe -m pytest -q -rA --tb=short
Remove-Item Env:RUN_OLLAMA_TESTS
```

Son gerçek tam çalıştırma: **135 passed in 40.16s**, başarısız/atlanan test yok. [Tam terminal çıktısı](docs/evidence/pytest-full.txt).

| Kapsam | Adet | Yöntem |
|---|---:|---|
| Mevcut motor, CLI ve SPEC vektörleri | 26 | Gerçek motor |
| MCP sunucusu | 35 | Gerçek stdio, validasyon ve ayrıca spy testleri |
| Ajan doğrulaması | 43 | Birim kontrolleri, mock model/HTTP ve gerçek MCP bağlantıları |
| Canlı Ollama + MCP / terminal | 5 | Gerçek `qwen2.5:7b`, gerçek stdio, çıkış kontrolü |
| Semantik SD regresyonları | 24 | Açık/belirsiz SD, eksik alanlar, çok turlu tamamlama ve gerçek MCP |
| Canlı semantik regresyonlar | 2 | Gerçek modelle netleştirmeden önce sıfır çağrı; tamamlandıktan sonra N=34 |

Ek teslim doğrulaması pytest paketinden ayrıdır:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_delivery suite
.\.venv\Scripts\python.exe -m scripts.verify_delivery demo
.\.venv\Scripts\python.exe -m scripts.verify_delivery negative
.\.venv\Scripts\python.exe -m scripts.verify_delivery audit
```

Bu komutlar `docs/evidence/` kayıtlarını yeniler. `suite` öncesi korunan dosya hash'lerini alır; `audit` bununla karşılaştırır. Düzeltme sonrası `negative` **9 PASS, 0 FAIL** üretti ve **0** çıkış koduyla tamamlandı. Önceki 8 PASS / 1 FAIL sonucu [ayrı kanıtta korunmuştur](docs/evidence/semantic-before-negative.json).

## Bilinen sınırlamalar

- “Her bir ölçümün standart sapması” artık yalnızca ölçüm SD'lerini sağlar; grup ortalamaları ve korelasyon eksikse soru sorulur. “Farkların standart sapması” veya `sd_diff` açık fark SD'sidir. Türü belirsiz SD'de hesaplama durur. Önceden çalışan “farkı ..., standart sapması ...” iyelikli ifadesi ve açık bir fark SD'si sorusuna verilen yanıt dar bağlam kurallarıyla desteklenir.
- Doğal dil katmanı muhafazakâr etiket/örüntü kontrolü kullanır; her Türkçe ifadeyi anlamaz. Alan adlarıyla netleştirme gerekebilir. Olumsuz/alternatifli ifadeler geniş biçimde reddedilir.
- `temperature=0` her model sürümünde aynı davranışı garanti etmez. Başka model veya SDK sürümünde canlı testler tekrarlanmalıdır.
- Transitif paketlerin tamamı kilitlenmiş değildir. Çalışan sürümler [ortam kaydındadır](docs/evidence/environment.json).
- 135 test mevcut kapsamdaki başarıdır; bütün olası girdilerin doğruluğunu veya gizli değerlendirmelerde başarıyı garanti etmez. Mevcut minimal N testi bağımsız N−1 güç kontrolü yapmaz.
- stdio yerel kullanım içindir; HTTP sunumu, uzak erişim güvenliği, genel amaçlı ajan veya klinik çalışma tasarımının tüm gereksinimleri bu kapsamda değildir.

## Teslim belgeleri

- [Nihai entegrasyon raporu ve kontrol listesi](docs/final-integration-report.md)
- [MCP Aşama 1 dokümanı](docs/mcp-phase1.md)
- [Ollama Aşama 2 dokümanı](docs/agent-phase2.md)
- [Mimari plan](MCP_OLLAMA_PLAN.md)

Sanal ortam, önbellek, yerel model dosyaları, `.env`, anahtarlar ve kişisel yollar teslim edilmemelidir. Git'e eklenecek dosyaları tek tek inceleyin; toplu eklemeden önce gizlilik ve clean-room kontrolünü [rapordaki listeden](docs/final-integration-report.md) tamamlayın.
