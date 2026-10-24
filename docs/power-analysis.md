# 3. kişi — Tek `power_analysis` MCP aracı

## Kapsam

Görselde verilen görev uygulandı: MCP sunucusu **yalnızca `power_analysis`** aracını yayımlar ve mevcut CLI ile aynı JSON nesnesini döndürür. `core_engine.py`, `cli.py`, SPEC, pyproject ve diğer grup üyelerinin testleri değiştirilmedi. Git komutu çalıştırılmadı; stage/commit/push yapılmadı.

Değişen kaynak: `mcp_server/server.py`. Eklenenler: `tests/test_power_analysis_contract.py` ve bu kullanım notu. Mevcut sunucu giriş noktası `python -m mcp_server` korunur; transport stdio, loglar stderr'dir.

## Girdi

| Alan | Tür | Kural |
|---|---|---|
| `test` | string | `t-paired` |
| `mode` | string | `a-priori` veya `post-hoc` |
| `tails` | integer | `1` veya `2` |
| `dz` | number | Pozitif etki büyüklüğü |
| `alpha` | number | 0 ile 1 arasında |
| `power` | number | Yalnızca a-priori için zorunlu; CLI'nin güç kuralları geçerli |
| `n_total` | integer | Yalnızca post-hoc için zorunlu |

Ortak ilk beş alan zorunludur. Bool, sayısal metin, null ve sonlu olmayan değerler JSON sayısı olarak kabul edilmez. Kullanılmayan moda ait parametreler CLI tarafından reddedilir. Hata cevabı `error`, `code`, `field` alanlarını ve MCP `isError=true` bilgisini taşır.

## Çıktı ve CLI ile eşitlik

A-priori örneği:

```json
{"test":"t-paired","mode":"a-priori","tails":1,"dz":0.5,"alpha":0.05,"power":0.95}
```

CLI ile aynı alanlar: `ncp`, `critical_t`, `df`, `n_total`, `actual_power`. Bu örnekte N=45, df=44.

Post-hoc örneği:

```json
{"test":"t-paired","mode":"post-hoc","tails":1,"dz":0.5,"alpha":0.05,"n_total":45}
```

CLI ile aynı alanlar: `ncp`, `critical_t`, `df`, `power`. df=44, güç yaklaşık 0.951240. **Mevcut CLI post-hoc JSON'una `n_total` eklemiyor; MCP de eklemez.** SPEC'teki post-hoc tablo `n_total` gösterse de bu görevde istenen CLI eşitliği korunmuş, diğer kişilerin koduna müdahale edilmemiştir. Repository'de ayrıca `CONTRACT.md` bulunmadığından mevcut CLI esas alınmıştır.

`structuredContent` ve JSON metin içerik bloğu aynı nesneyi taşır. Ek `result` zarfı, `sample_size`, `delta` veya MCP'ye özgü hesaplama alanları eklenmez. İstatistiksel hesaplama yeniden yazılmaz; `cli.parser()` ve `cli.execute()` yeniden kullanılır. CLI'nin print eden `run()` fonksiyonu sunucuda çağrılmadığı için stdout'a protokol dışı JSON yazılmaz.

## PowerShell

Mevcut Python 3.13 proje ortamında:

```powershell
.\.venv\Scripts\python.exe -m mcp_server
```

MCP istemcisi bu komutu alt süreç olarak açmalıdır. İnteraktif sohbet komutu değildir.

Doğrulanan komut:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_power_analysis_contract.py tests/test_cli.py tests/test_core.py tests/test_validation.py -q
```

Gerçek sonuç: **79 passed in 36.31s**. Bunun 33'ü yeni tek araç MCP testi, 46'sı mevcut motor/CLI/doğrulama testidir. MCP SDK 1.30.0 kullanıldı. Yeni testler gerçek stdio discovery, iki modda CLI eşitliği, CLI hata nesneleri, katı JSON türleri, eski araç adının reddi ve EOF sonrası kapanışı doğrular.

## Ollama ajanı

İlk tek araç değişikliği yalnızca MCP sunucusunu kapsıyordu. Sonraki kullanıcı isteğiyle ajan ve ilgili entegrasyon testleri de `power_analysis` sözleşmesine uyarlandı. `python -m agent` artık bu tek araçla a-priori ve post-hoc analiz yapar. [Güncel kullanım ve test kaydı](agent-power-analysis.md). Yukarıdaki 79 test önceki MCP doğrulamasıdır; eski aşama raporlarındaki 135 test sonucu da önceki üç araçlı sürüme aittir.
