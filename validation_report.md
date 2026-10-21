# [REA] G*Power Bağımsız Doğrulama Raporu — Görev 2

**Tarih:** 21 Ekim 2026  
**Referans uygulama:** G*Power 3.1.9.7 (Windows)  
**Modül:** t tests → Means: Difference between two dependent means (matched pairs) → A priori  
**Python ortamı (kullanıcının terminal çıktısı):** Python 3.14.3, pytest 9.1.1 (Windows); NumPy/SciPy sürümleri kaydedilmedi.

## Bulgular

Kullanıcı tarafından G*Power üzerinde çalıştırılıp ekran görüntüsüyle belgelenen 5 senaryoda gerekli örneklem büyüklüğü (N), serbestlik derecesi (df) ve diğer sayısal çıktılar SPEC.md §5 vektörleri ve Python CLI referans değerleriyle belirtilen 1e-5 mutlak tolerans içinde eşleşti.

| Vektör | Tail | dz | α | Hedef güç | G*Power N | Python N | df | G*Power actual power | Kanıt |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| V-01 | two-tailed | 0.5 | 0.05 | 0.80 | 34 | 34 | 33 | 0.8077775 | [Ekran görüntüsü](evidence/V-01.JPG) |
| V-02 | two-tailed | 0.2 | 0.05 | 0.80 | 199 | 199 | 198 | 0.8016910 | [Ekran görüntüsü](evidence/V-02.JPG) |
| V-03 | two-tailed | 0.8 | 0.05 | 0.95 | 23 | 23 | 22 | 0.9558497 | [Ekran görüntüsü](evidence/V-03.JPG) |
| V-04 | one-tailed | 0.5 | 0.05 | 0.80 | 27 | 27 | 26 | 0.8118316 | [Ekran görüntüsü](evidence/V-04.JPG) |
| V-05 | two-tailed | 0.3 | 0.01 | 0.90 | 169 | 169 | 168 | 0.9006992 | [Ekran görüntüsü](evidence/V-05.JPG) |

**Gözlenen N eşleşmesi:** 5/5 = %100 (yalnızca bu beş bağımsız gözlem için).
**Yerel otomatik testler:** Kullanıcının paylaştığı `python -m pytest -v` çıktısında 26/26 başarılı, 2.60 saniye.
**CLI örnek çıktısı:** `python cli.py --effect-size 0.5 --alpha 0.05 --power 0.80` → `sample_size=34`, `df=33`, `delta=2.9154759474226504`, `critical_t=2.0345152974493383`, `actual_power=0.8077775012792737`.

## Kanıtların kaynağı ve sınırlar

- `evidence/V-01.JPG`–`V-05.JPG` dosyaları G*Power uygulamasından kullanıcı tarafından sağlanan ekran görüntüleridir; orijinal program dosyaları, decompile çıktısı veya GPower.exe repoya eklenmemiştir.
- Python tarafındaki V-02–V-05 sayısal değerleri SPEC.md ve geçen testlerdeki vektörlerden alınmıştır; bunlar her biri için ayrı terminal çalıştırma kayıtları değildir.
- Bu 5 senaryonun başarılı olması hocanın gizli testlerinde %90 başarıyı garanti etmez. Daha çok bağımsız test, özellikle sınır ve hata durumları önerilir.
- REA araçlarının kullanımı ve iki ajan arasında clean-room ayrımı için ayrı süreç kayıtları gerekiyorsa ayrıca belgelendirilmelidir.

## Tekrarlama komutları

```cmd
python -m pytest -v
python cli.py --effect-size 0.5 --alpha 0.05 --power 0.80
python cli.py --effect-size 0.2 --alpha 0.05 --power 0.80
python cli.py --effect-size 0.8 --alpha 0.05 --power 0.95
python cli.py --effect-size 0.5 --alpha 0.05 --power 0.80 --tails one-tailed
python cli.py --effect-size 0.3 --alpha 0.01 --power 0.90
```
