# SPECIFICATION: G*Power Paired Samples t-Test (A Priori Power Analysis)

## 1. Genel Bakış ve Amaç
Bu doküman, G*Power 3.1 yazılımında bulunan **"t tests -> Means: Difference between two dependent means (matched pairs)"** modülünün davranışını ve matematiksel modelini tanımlar. Bu spesifikasyon, Clean-Room tersine mühendislik ilkelerine uygun olarak, kaynak koda bakılmaksızın sıfırdan aynı sonuçları üreten bağımsız, güvenli ve dayanıklı bir hesaplama motoru geliştirmek için hazırlanmıştır.

---

## 2. Girdi Parametreleri (Input Parameters)

### 2.1. Temel Parametreler
| Parametre | Değişken Adı | Veri Tipi | Geçerli Aralık / Format | Tanım |
|---|---|---|---|---|
| **Tails** | `tails` | string / enum | `'one-tailed'`, `'two-tailed'` | Testin yönü (Tek yönlü / Çift yönlü) |
| **Effect size $d_z$** | `effect_size_dz` | float | $d_z > 0$ | Standardize edilmiş etki büyüklüğü |
| **$\alpha$ err prob** | `alpha` | float | $0 < \alpha < 1$ (Örn: `0.05`) | Tip I hata olasılığı |
| **Power ($1 - \beta$ err prob)** | `target_power` | float | $0 < 1 - \beta < 1$ (Örn: `0.80`) | Hedeflenen istatistiksel güç |

Sayısal girdiler `int`, `float` veya `numbers.Real` ile uyumlu sayısal türler (örn. `numpy.int64`, `numpy.float64`, `fractions.Fraction`) olmalıdır. `bool`, `str`, `decimal.Decimal` ve diğer türler kabul edilmez (bkz. Bölüm 6, adım 1).

### 2.2. Klinik / Tansiyon Senaryosu Girdileri ("Determine" Modülü)
Kullanıcı doğrudan $d_z$ yerine klinik değerleri girerse, $d_z$ şu formüllerle türetilir:

1. **Farklar Üzerinden (From differences):**
   $$d_z = \frac{\vert{}\mu_D\vert{}}{\sigma_D}$$
   * $\mu_D$ (`mean_diff`): Öncesi-sonrası fark ortalaması ($\vert{}\mu_D\vert{} > 0$)
   * $\sigma_D$ (`sd_diff`): Farkların standart sapması ($\sigma_D > 0$)

2. **Grup İstatistikleri Üzerinden (From group parameters):**
   $$\text{radicand} = \sigma_1^2 + \sigma_2^2 - 2 \cdot r \cdot \sigma_1 \cdot \sigma_2$$
   $$\sigma_D = \sqrt{\text{radicand}}$$
   $$d_z = \frac{\vert{}\mu_1 - \mu_2\vert{}}{\sigma_D}$$
   * $\mu_1, \mu_2$: Öncesi ve sonrası grup ortalamaları ($\vert{}\mu_1 - \mu_2\vert{} > 0$)
   * $\sigma_1, \sigma_2$: Grup standart sapmaları ($\sigma_1 > 0, \sigma_2 > 0$)
   * $r$: Gruplar arası korelasyon ($-1 \le r \le 1$)
   * *Sayısal Kararlılık Kuralı (göreli eşik):* $\text{radicand} \le 10^{-12} \cdot (\sigma_1^2 + \sigma_2^2)$ ise $\sigma_D = 0$ kabul edilir ve sıfıra bölme hatası tetiklenir. Eşik, birimden bağımsız olması için mutlak değil göreli tanımlanmıştır.

---

## 3. Çıktı Parametreleri (Output Parameters)

| Çıktı Değişkeni | Değişken Adı | Tip | Tanım |
|---|---|---|---|
| **Total sample size** | `sample_size` ($N$) | integer | Gereken toplam eşleşmiş çift/örneklem sayısı ($N \ge 2$) |
| **Degrees of freedom** | `df` | integer | Serbestlik derecesi ($df = N - 1$) |
| **Noncentrality parameter $\delta$** | `delta` | float | Merkezi olmama parametresi ($\delta = d_z \cdot \sqrt{N}$) |
| **Critical t** | `critical_t` ($t_{crit}$) | float | Karar eşiği Student's $t$ değeri |
| **Actual power** | `actual_power` | float | Tam sayı $N$ örneği ile ulaşılan gerçek güç |

---

## 4. Matematiksel Formülasyon ve Algoritma

### 4.1. Serbestlik Derecesi ve Noncentrality
$$df = N - 1$$
$$\delta = d_z \cdot \sqrt{N}$$

### 4.2. Kritik $t$ ($t_{crit}$) Hesabı
* **Çift Yönlü (`two-tailed`):**
  $$p = 1 - \frac{\alpha}{2} \implies t_{crit} = Q_t\left(1 - \frac{\alpha}{2}, \, df\right)$$
* **Tek Yönlü (`one-tailed`):**
  $$p = 1 - \alpha \implies t_{crit} = Q_t(1 - \alpha, \, df)$$

### 4.3. Güç (Power) Hesabı
* **Çift Yönlü (`two-tailed`):**
  $$\text{Actual Power} = 1 - F_{nct}(t_{crit}; \, df, \, \delta) + F_{nct}(-t_{crit}; \, df, \, \delta)$$
* **Tek Yönlü (`one-tailed`):**
  $$\text{Actual Power} = 1 - F_{nct}(t_{crit}; \, df, \, \delta)$$

### 4.4. Örneklem Büyüklüğü ($N$) Arama Algoritması
1. $N = 2$ olarak başlat. Üst arama sınırı $N_{\max} = 100\,000$'dir.
2. $df = N - 1$ ve $\delta = d_z \cdot \sqrt{N}$ hesapla.
3. $t_{crit}$ değerini hesapla.
4. $F_{nct}$ üzerinden mevcut gücü (`current_power`) hesapla.
5. Eğer $\text{current\_power} \ge \text{target\_power}$ ise dur ve değerleri döndür.
6. Eğer $N = N_{\max}$ adımında da hedef güce ulaşılamazsa dur ve `RuntimeError: Sample size exceeded maximum threshold` hatası fırlat.
7. Değilse $N = N + 1$ yap ve 2. adıma dön.

> **Performans Notu:** Referans algoritma doğrusal artımdır ($N = N + 1$). Ancak aynı minimal tam sayı $N$'i garanti etmek şartıyla ikili arama (binary search) veya üstel sıçramalı arama (exponential search) optimizasyonları uygulanabilir. Bu optimizasyonlar güç fonksiyonunun $N$'e göre monoton artan olmasına dayanır; bu, yalnızca Bölüm 4.5'teki NaN kuralına uyulursa sayısal olarak güvenilirdir.

### 4.5. Sayısal Uygulama Notu: `NaN` Dönen Merkezi Olmayan $t$ CDF'i
Bazı kütüphane sürümlerinde merkezi olmayan $t$ CDF'i ($F_{nct}$), matematiksel olarak geçerli girdilerde `NaN` döndürebilir. Örnek: scipy 1.15 ve sonrasında $d_z = 0.3$, $\alpha = 0.001$, $N < 3000$ için yaklaşık yarısı `NaN` (scipy 1.10–1.13'te bu bölgede `NaN` gözlenmedi, ancak sürüm bağımlılığı yarın değişebilir).

* `NaN` bir güç değeri **değildir**; `NaN >= target_power` karşılaştırmasının "güç yetersiz" sonucuna düşmesine izin verilmemelidir. Bu, doğrusal algoritmada bile yanlış $N$ üretir (gerçek değerden birkaç fazla; örn. 356 yerine 357, 795 yerine 801); üstel/ikili aramada ise çok daha büyük sapmalara yol açar (örn. 277 yerine 1574).
* Bir $F_{nct}$ değeri sonlu değilse, aynı değer **sayısal integrasyonla** hesaplanmalıdır:
  $$F_{nct}(x;\, df,\, \delta) = \int_0^{\infty} \Phi\!\left(x\sqrt{\tfrac{v}{df}} - \delta\right) f_{\chi^2_{df}}(v)\, dv$$
  Burada $\Phi$ standart normal CDF'i, $f_{\chi^2_{df}}$ ise $df$ serbestlik dereceli ki-kare yoğunluğudur. İntegrasyon sınırları için $\chi^2_{df}$'nin $10^{-14}$ ve $1 - 10^{-14}$ kuantilleri kullanılabilir.
* Yedek yöntem de sonlu bir değer üretemezse motor `RuntimeError: Power computation failed` fırlatmalıdır (sessizce yanlış $N$ döndürmek yerine).
* Bölüm 5.1'deki V-06…V-11 vektörleri bu bölgeleri kapsar ve bağımsız olarak sayısal integrasyonla doğrulanmıştır.

---

## 5. Doğrulama Vektörleri (Ground-Truth Test Vectors)

### 5.1. Temel Vektörler (Başarılı Senaryolar)
| No | Tails | $d_z$ | $\alpha$ | Target Power | Beklenen $N$ | Beklenen $df$ | Beklenen $\delta$ | Beklenen $t_{crit}$ | Beklenen Power |
|---|---|---|---|---|---|---|---|---|---|
| **V-01** | `two-tailed` | 0.5 | 0.05 | 0.80 | **34** | 33 | 2.915476 | 2.034515 | 0.807778 |
| **V-02** | `two-tailed` | 0.2 | 0.05 | 0.80 | **199** | 198 | 2.821347 | 1.972017 | 0.801691 |
| **V-03** | `two-tailed` | 0.8 | 0.05 | 0.95 | **23** | 22 | 3.836665 | 2.073873 | 0.955850 |
| **V-04** | `one-tailed` | 0.5 | 0.05 | 0.80 | **27** | 26 | 2.598076 | 1.705618 | 0.811832 |
| **V-05** | `two-tailed` | 0.3 | 0.01 | 0.90 | **169** | 168 | 3.900000 | 2.605410 | 0.900699 |
| **V-06** | `two-tailed` | 0.3 | 0.001 | 0.95 | **277** | 276 | 4.992995 | 3.326125 | 0.950873 |
| **V-07** | `two-tailed` | 0.3 | 0.001 | 0.99 | **356** | 355 | 5.660389 | 3.318143 | 0.990006 |
| **V-08** | `two-tailed` | 0.5 | 0.001 | 0.999 | **169** | 168 | 6.500000 | 3.349379 | 0.999045 |
| **V-09** | `two-tailed` | 0.1 | 0.001 | 0.99 | **3161** | 3160 | 5.622277 | 3.293608 | 0.990016 |
| **V-10** | `two-tailed` | 0.05 | 0.001 | 0.90 | **8367** | 8366 | 4.573565 | 3.291690 | 0.900001 |
| **V-11** | `two-tailed` | 20 | 0.05 | 0.80 | **2** | 1 | 28.284271 | 12.706205 | 0.973524 |

V-06…V-11, `NaN` dönen $F_{nct}$ bölgelerini (Bölüm 4.5) sınayan regresyon vektörleridir. V-11'de $N = 2$ (alt sınır) yeterlidir; bu noktada doğrudan $F_{nct}$ `NaN` döndürebilir ve `NaN` "yetersiz güç" sayılırsa yanlışlıkla $N = 3$ bulunur.

### 5.2. Klinik Tansiyon & Determine Doğrulama Vektörleri
Tüm Determine vektörlerinde `tails = 'two-tailed'`, $\alpha = 0.05$, target power $= 0.80$ kullanılır.

| No | Girdiler | Türetilen $\sigma_D$ | Türetilen $d_z$ | Beklenen sonuç |
|---|---|---|---|---|
| **V-DET-01** (Farklar) | $\mu_D = 5.0,\ \sigma_D = 10.0$ | 10.0 | 0.5 | $N = 34$ (V-01 ile eşleşir) |
| **V-DET-02** (Gruplar) | $\mu_1 = 140,\ \mu_2 = 135,\ \sigma_1 = 10,\ \sigma_2 = 10,\ r = 0.5$ | 10.0 | 0.5 | $N = 34$ |
| **V-DET-03** (Çok küçük σ, göreli eşik) | $\mu_1 - \mu_2 = 5\times10^{-7},\ \sigma_1 = \sigma_2 = 10^{-7},\ r = 0.5$ | $10^{-7}$ | 5.0 | $N = 3$, $df = 2$, $\delta = 8.660254$, $t_{crit} = 4.302653$, power $= 0.975462$ |

V-DET-03, mutlak $10^{-12}$ eşiğinin geçerli girdiyi yanlışlıkla reddedeceği (radikand $\approx 10^{-14}$) ve göreli eşiğin bunu doğru kabul edeceği durumu sınar.

### 5.3. Negatif Test Vektörleri (Hata Senaryoları)
Aksi belirtilmedikçe geçerli taban girdi: `tails='two-tailed'`, $d_z = 0.5$, $\alpha = 0.05$, target power $= 0.80$. Beklenen hata türü ve mesajı birebir eşleşmelidir.

| No | Değişen girdi | Beklenen istisna |
|---|---|---|
| **E-01** | `tails = 'left'` | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-02** | $d_z = 0$ | `ValueError: Effect size must be strictly positive` |
| **E-03** | $d_z = -0.5$ | `ValueError: Effect size must be strictly positive` |
| **E-04** | $\alpha = 1.0$ | `ValueError: Alpha must be between 0 and 1` |
| **E-05** | target power $= 0$ | `ValueError: Target power must be between 0 and 1` |
| **E-06** | $d_z = $ `NaN` | `ValueError: Parameters cannot be NaN, Infinite or empty` |
| **E-07** | $d_z = $ `"0.5"` (string) | `TypeError: Numeric parameters must be int or float` |
| **E-08** | $d_z = 0.001$ | `RuntimeError: Sample size exceeded maximum threshold` ($N_{\max}$'te güç $\approx 0.0615$) |
| **E-09** | Determine/Farklar: $\mu_D = 0,\ \sigma_D = 10$ | `ValueError: Mean difference cannot be zero (no detectable effect)` |
| **E-10** | Determine/Farklar: $\mu_D = 5,\ \sigma_D = 0$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` |
| **E-11** | Determine/Farklar: $\mu_D = 5,\ \sigma_D = -1$ | `ValueError: Standard deviations must be strictly positive` |
| **E-12** | Determine/Gruplar: $\mu_1 - \mu_2 = 5,\ \sigma_1 = \sigma_2 = 10,\ r = 1.0$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` |
| **E-13** | Determine/Gruplar: aynı değerler, $r = 1.5$ | `ValueError: Correlation must be between -1 and 1` (kontrol sırası testi: E-12 değil bu hata gelmelidir) |
| **E-14** | Determine/Gruplar: $\sigma_1 = 0,\ \sigma_2 = 10,\ r = 0.5$ | `ValueError: Standard deviations must be strictly positive` |
| **E-15** | $d_z = $ `None`, $\alpha = $ `"x"` | `ValueError: Parameters cannot be NaN, Infinite or empty` (parametre sırası: ilk parametre `None`) |
| **E-16** | $d_z = $ `"x"`, $\alpha = $ `None` | `TypeError: Numeric parameters must be int or float` (parametre sırası: ilk parametre geçersiz tür) |

### 5.4. Tolerans Kuralı
* $N$ ve $df$ için **tam eşitlik** aranır.
* $\delta, t_{crit}, \text{actual\_power}$ için mutlak tolerans $\vert{}a - b\vert{} \le 10^{-5}$ kabul edilir.

---

## 6. Uç Durumlar ve Hata Yönetimi (Edge Cases)

Doğrulamalar **aşağıdaki sırayla** yapılır; ilk başarısız kontrol hatayı belirler ve sonrakiler çalıştırılmaz. Böylece aynı girdi birden fazla kuralı ihlal ettiğinde sonuç deterministik olur.

| Sıra | Kontrol | İstisna |
|---|---|---|
| 1 | Sayısal girdilerden biri `numbers.Real` değil veya `bool` (`str`, `Decimal` vb.; `None` hariç) | `TypeError: Numeric parameters must be int or float` |
| 2 | Girdilerden herhangi biri `None`, `NaN` veya `inf` / `-inf` | `ValueError: Parameters cannot be NaN, Infinite or empty` |
| 3 | `tails` değeri `'one-tailed'` veya `'two-tailed'` dışında | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| 4 | $\alpha \le 0$ veya $\alpha \ge 1$ | `ValueError: Alpha must be between 0 and 1` |
| 5 | $\text{target\_power} \le 0$ veya $\text{target\_power} \ge 1$ | `ValueError: Target power must be between 0 and 1` |
| 6 | *(Gruplar)* $r < -1$ veya $r > 1$ | `ValueError: Correlation must be between -1 and 1` |
| 7 | *(Gruplar)* $\sigma_1 \le 0$ veya $\sigma_2 \le 0$; *(Farklar)* $\sigma_D < 0$ | `ValueError: Standard deviations must be strictly positive` |
| 8 | *(Farklar)* $\sigma_D = 0$; *(Gruplar)* radikand $\le 10^{-12} \cdot (\sigma_1^2 + \sigma_2^2)$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` |
| 9 | *(Determine)* $\mu_D = 0$ veya $\vert{}\mu_1 - \mu_2\vert{} = 0$ | `ValueError: Mean difference cannot be zero (no detectable effect)` |
| 10 | $d_z \le 0$ (doğrudan girilen veya türetilen) | `ValueError: Effect size must be strictly positive` |
| 11 | $N = N_{\max}$ ($100\,000$) değerinde de güç hedefine ulaşılamadı | `RuntimeError: Sample size exceeded maximum threshold` |

**Notlar:**
* **Adım 1 ve 2'nin parametre sırası:** Bu iki adım tüm girdiler için ayrı ayrı değil, parametreler **imzadaki sırayla** işlenir ve her parametre kendi içinde şu sırayla denetlenir: `None` → tür/`bool` → `NaN`/`inf`. İlk geçersiz parametre hatayı belirler. İmza sırası: `power_matched_pairs(effect_size_dz, alpha, target_power, tails)`; Farklar için `(mean_diff, sd_diff)`; Gruplar için `(mean1, mean2, sd1, sd2, correlation)`. Örn. `effect_size_dz=None, alpha="x"` → `ValueError`; `effect_size_dz="x", alpha=None` → `TypeError` (E-15, E-16).
* Sıfıra bölme durumları tek bir türde toplanmıştır: $\sigma_D$'nin tam sıfır olması (doğrudan girilmiş ya da hesaplanmış) her zaman `ZeroDivisionError` verir; yalnızca **negatif** standart sapma `ValueError` verir.
* Adım 1'de `bool`, Python'da `int` alt sınıfı olsa da bilinçli olarak reddedilir.
* Adım 11, Bölüm 4.4'teki 6. adım ile aynı koşuldur: $N = N_{\max}$ için güç kontrolü yapıldıktan sonra hâlâ yetersizse hata atılır.