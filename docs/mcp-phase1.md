# MCP sunucusu — Aşama 1

## Kapsam

Mevcut `core_engine.py` fonksiyonlarını kullanan stdio sunucusu. Ollama ajanı bu aşamada geliştirilmedi. `core_engine.py`, `cli.py`, `SPEC.md`, `requirements.txt`, mevcut testler ve README değiştirilmedi. Önceden oluşturulan `MCP_OLLAMA_PLAN.md` korundu. Commit veya push yapılmadı.

Dal: `codex/mcp-server-phase1`.

## Windows PowerShell

Komutları repository kökünde çalıştırın. Doğrulanan ortam Python 3.13.4'tür. Mevcut `.venv` varsa yeniden oluşturmayın; önce yorumlayıcıyı kontrol edin.

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m mcp_server
```

Yeni bir checkout için önce kurulu Python 3.13 yorumlayıcınızla `python -m venv .venv` çalıştırın. Aktivasyon gerekmez; yukarıdaki komutlar doğrudan sanal ortamı kullanır. Test gerekmeyen kurulumda `requirements.txt` ve `requirements-integration.txt` yeterlidir.

Sunucu etkileşimli bir sohbet uygulaması değildir; stdin üzerinden MCP JSON-RPC mesajları bekler. Bir MCP istemcisinde command olarak sanal ortamın **mutlak** `python.exe` yolunu, args olarak `-m`, `mcp_server`, cwd olarak repository'nin mutlak yolunu kullanın. Yolları shell komutu halinde birleştirmek yerine ayrı argümanlar olarak iletin.

stdout protokol içindir. Loglar stderr'e gider. stdin EOF olduğunda sunucu kapanır; istemci kendi başlattığı sürecin yaşam döngüsünü yönetmelidir.

## Araç sözleşmeleri

Tüm parametreler zorunludur; varsayılan uygulanmaz.

| Araç | Özel girdiler | Motor çağrısı |
|---|---|---|
| `calculate_sample_size` | `effect_size_dz` | `power_matched_pairs` |
| `calculate_from_differences` | `mean_diff`, `sd_diff` | `calculate_dz_from_differences` → `power_matched_pairs` |
| `calculate_from_groups` | `mean1`, `mean2`, `sd1`, `sd2`, `correlation` | `calculate_dz_from_groups` → `power_matched_pairs` |

Ortak girdiler: `alpha`, `target_power`, `tails`. Yön yalnızca `one-tailed` veya `two-tailed` olabilir. Sayısal alanlar JSON number kabul eder; bool, metin, null ve sonlu olmayan değerler reddedilir. Bilinmeyen ve eksik alanlar reddedilir. Sayısal metinler sayıya çevrilmez.

Alanlar arası ve istatistiksel aralık kontrolleri motorda kalır. Determine araçları önce dz fonksiyonunu, sonra güç fonksiyonunu çağırır; hata önceliği bu sırayı izler. Şema doğrulama hataları motor hatalarından önce oluşabilir. Motorun tüm parametreleri için yeni bir küresel validasyon sırası vaat edilmez.

Başarılı `structuredContent` doğrudan şu beş alanı içerir: `sample_size` (N), `df`, `delta`, `critical_t`, `actual_power`. Aynı sonuç geriye uyumlu metin içerik bloğunda JSON olarak da bulunur; `outputSchema` discovery sırasında yayımlanır. N, tamamlanmış eşleşmiş çift/katılımcı sayısıdır; toplam ölçüm sayısı veya kayıp payı eklenmiş örneklem değildir.

Beklenen motor istisnaları `ToolError` üzerinden `isError=true` cevabına çevrilir; özgün istisna adı ve mesajı hata metninde korunur. SDK bu metne araç adı gibi bağlam ekleyebilir. Başarısız cevap başarılı sonuç olarak sunulmaz.

Örnek argümanlar: `effect_size_dz=0.5`, `alpha=0.05`, `target_power=0.80`, `tails="two-tailed"`. Beklenen N=34, df=33, delta≈2.915476, critical_t≈2.034515, actual_power≈0.807778.

## SDK ve bağımlılıklar

Resmî Python paketi `mcp==1.30.0`, `mcp.server.fastmcp.FastMCP` API'si kullanıldı. `pydantic==2.14.1` ile katı sayısal doğrulama ve çıktı modeli tanımlandı. Test bağımlılığı `pytest==9.1.1`. Doğrulama ortamında NumPy 2.5.4 ve SciPy 1.18.1 kuruldu. Temel bağımlılık aralıkları değiştirilmedi; transitif bağımlılıkların tamamı kilitlenmiş değildir.

SDK v1 FastMCP API'si için sürüm sabitlenmiştir; v2'ye otomatik geçiş yapılmaz. SDK'nın kurulu kaynakları incelendi. Varsayılan argüman modelinin fazladan alanları göz ardı etmesi nedeniyle yalnızca bu sunucuya ait `StrictFastMCP` alt sınıfı, public `list_tools` ve `call_tool` metotlarında ek alanları reddeder ve discovery şemasında `additionalProperties=false` yayımlar. SDK dosyaları değiştirilmedi.

Kaynak: https://py.sdk.modelcontextprotocol.io/v1/

## Testler ve doğrulama kaydı

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_server.py -q
.\.venv\Scripts\python.exe -m pip check
```

22 Ekim 2026 tarihindeki tam çalıştırma: **61 başarılı, 0 başarısız** (26 mevcut + 35 yeni MCP testi). `pip check`: bozuk bağımlılık yok.

Yeni testler gerçek `ClientSession` ve `stdio_client` kullanarak Python alt süreci başlatır; initialize, discovery, üç araç üzerinden N=34 ve beş çıktı alanı, tüm sayısal alanlarda bool/string/null reddi, eksik/ek alan, aralık ve yön hataları, motor hata mesajlarını doğrular. Nonfinite sayılar standart JSON olmadığından taşıma öncesi adaptör çağrısında sınanır. Ayrı spy testleri doğru motor fonksiyonları ve argümanlarını kontrol eder. Ayrı subprocess testi gerçek initialize cevabını, stdout'un yalnızca JSON-RPC olmasını ve stdin EOF sonrası sıfır çıkış kodunu doğrular. Testlerde başlatma/çağrı/kapanış için süre sınırları vardır.

İlk kısıtlı ortam denemelerinde Python yol uyarısı/ensurepip sorunu yaşandı; pip kurulumu gerekli ortam erişimiyle tamamlandı. Kısıtlı ortamda tamamlanmayan iki test çalıştırması iptal edildi; başarılı kabul edilmedi. Nihai tam test çalıştırması gerçek Windows alt süreç erişimiyle tamamlandı. Yeni bir ortamda benzer erişim sorunu oluşursa testler atlanmamalı; uygun süreç izinleriyle yeniden çalıştırılmalı.

## Sonraki aşama

Bu aşamada çözümsüz işlevsel hata tespit edilmedi. Ollama bağlantısı veya model testi yapılmadı. Sonraki aşama için kullanıcı onayı beklenir; gelecekteki ajan için kullanıcı tarafından belirtilen model `qwen2.5:7b` olacaktır.
