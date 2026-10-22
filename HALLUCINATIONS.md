# LLM Halüsinasyon ve Hata Analiz Günlüğü (HALLUCINATIONS.md)

### 1. SciPy nct.cdf Sayısal İntegrasyon Hatası (Kritik)
* **Halüsinasyon / Hata:** LLM başlangıçta standart `scipy.stats.nct.cdf` fonksiyonunun her aralıkta doğru çalıştığını varsaydı.
* **Gerçek Durum:** Küçük $\alpha$ ($0.001$) ve uç $d_z$ ($20.0$) değerlerinde SciPy'nin C kütüphanesi taşma yaparak `NaN` döndürdü.
* **Düzeltme:** Kod `_nct_cdf_quad` fonksiyonu ile sayısal ki-kare integrasyonuna düşürüldü.

### 2. Bağımsız vs. Eşleştirilmiş Serbestlik Derecesi Karışıklığı
* **Halüsinasyon:** LLM bağımsız iki grup t-testi ile eşleştirilmiş t-testini karıştırıp $df = 2N - 2$ formülünü öne sürdü.
* **Gerçek Durum:** Eşleştirilmiş t-testinde fark serisi tek bir vektör oluşturduğundan serbestlik derecesi kesinlikle $df = N - 1$'dir.

### 3. Mutlak Eşik Hatası (Determine Modülü)
* **Halüsinasyon:** Standart sapma farkı için mutlak $10^{-12}$ alt sınırı belirlendi.
* **Gerçek Durum:** Biyokimyasal veya mikroskobik verilerde ($10^{-7}$) bu eşik meşru verileri hatalı biçimde sıfır kabul etti. Göreli formüle geçildi: `radicand <= (1e-12 * scale)`.