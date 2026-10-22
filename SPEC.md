# SPECIFICATION: G*Power Paired Samples t-Test (A Priori & Post-Hoc Power Analysis)

## 1. Genel Bakış ve Amaç
Bu doküman, G*Power 3.1.9.7 yazılımındaki **"t tests -> Means: Difference between two dependent means (matched pairs)"** modülünün (`CONTRACT.md` kimliği: `t-paired`) davranışını ve matematiksel modelini tanımlar. Spesifikasyon, Clean-Room tersine mühendislik ilkelerine uygun olarak, kaynak koda bakılmaksızın aynı sonuçları üreten bağımsız ve dayanıklı bir hesaplama motoru geliştirmek için hem **a-priori** hem de zorunlu **post-hoc** modlarını kapsar.

---

## 2. Girdi Parametreleri (Input Parameters)

### 2.1. Temel Parametreler
| Parametre | Değişken Adı | CLI Bayrağı | Veri Tipi | Geçerli Aralık / Format | Tanım |
|---|---|---|---|---|---|
| **Tails** | `tails` | `--tails` | int / str | `1`, `2`, `'one-tailed'`, `'two-tailed'` | Testin yönü. `bool`, `None`, `"1"`, `"2"`, `1.0`, `2.0` reddedilir |
| **Effect size $d_z$** | `effect_size_dz` | `--dz` | float | $d_z > 0$ | Standardize edilmiş etki büyüklüğü |
| **$\alpha$ err prob** | `alpha` | `--alpha` | float | $0 < \alpha < 1$ (Varsayılan: `0.05`) | Tip I hata olasılığı |
| **Power ($1 - \beta$)** | `target_power` | `--power` | float | $0 < 1 - \beta < 1$ (Varsayılan: `0.80`) | *(Yalnızca a-priori)* Hedeflenen güç |
| **Total sample size** | `n_total` | `--n_total` | integer | $2 \le N \le 100\,000$, tam sayı değerli | *(Yalnızca post-hoc)* Toplam eşleşmiş çift sayısı |

**Sayısal tür kuralı:** Sayısal girdiler `numbers.Real` ile uyumlu olmalıdır (`int`, `float`, `numpy.int64`, `numpy.float64`, `fractions.Fraction`). `bool`, `str`, `decimal.Decimal` ve diğer türler kabul edilmez (Bölüm 6, Adım 1).

**`n_total` tam sayı kuralı:** `n_total` türü ne olursa olsun tam sayı değerli olmalıdır. `34`, `34.0`, `numpy.int64(34)` ve `Fraction(68, 2)` kabul edilir ve `34` olarak işlenir. `34.5` ve `Fraction(69, 2)` `TypeError` verir; sessizce kesilmez.

### 2.2. Klinik / Tansiyon Senaryosu Girdileri ("Determine" Modülü)
Kullanıcı doğrudan $d_z$ yerine klinik değerleri girerse $d_z$ şu formüllerle türetilir:

1. **Farklar Üzerinden (From differences)** — `calculate_dz_from_differences(mean_diff, sd_diff)`:
   $$d_z = \frac{\vert\mu_D\vert}{\sigma_D}$$
   * $\mu_D$ (`mean_diff`): Öncesi-sonrası fark ortalaması ($\vert\mu_D\vert > 0$)
   * $\sigma_D$ (`sd_diff`): Farkların standart sapması ($\sigma_D > 0$)

2. **Grup İstatistikleri Üzerinden (From group parameters)** — `calculate_dz_from_groups(mean1, mean2, sd1, sd2, correlation)`:
   $$\text{radicand} = \sigma_1^2 + \sigma_2^2 - 2 \cdot r \cdot \sigma_1 \cdot \sigma_2, \qquad \sigma_D = \sqrt{\text{radicand}}, \qquad d_z = \frac{\vert\mu_1 - \mu_2\vert}{\sigma_D}$$
   * $\mu_1, \mu_2$: Öncesi ve sonrası grup ortalamaları ($\vert\mu_1 - \mu_2\vert > 0$)
   * $\sigma_1, \sigma_2$: Grup standart sapmaları ($\sigma_1 > 0,\ \sigma_2 > 0$)
   * $r$: Gruplar arası korelasyon ($-1 \le r \le 1$)
   * *Sayısal kararlılık kuralı (göreli eşik):* $\text{radicand} \le 10^{-12} \cdot (\sigma_1^2 + \sigma_2^2)$ ise $\sigma_D = 0$ kabul edilir ve `ZeroDivisionError` fırlatılır. Eşik, birimden bağımsız olması için mutlak değil göreli tanımlanmıştır (mutlak $10^{-12}$ eşiği, $\sigma \sim 10^{-7}$ olan meşru verileri hatalı biçimde sıfır sayar; bkz. V-DET-03).

---

## 3. Çıktı Parametreleri (CONTRACT.md Çıktı Şeması)

Çıktılar stdout üzerine **tek satır JSON nesnesi** olarak döner. Anahtar kümesi aşağıdakilerle **birebir** aynıdır; fazladan anahtar (örn. `sample_size`, `delta`) üretilmez.

### 3.1. a-priori Modu Çıktısı
| Çıktı Değişkeni | Anahtar Adı | Tip | Tanım |
|---|---|---|---|
| **Noncentrality parameter $\delta$** | `ncp` | float | $\delta = d_z \cdot \sqrt{N}$ |
| **Critical t** | `critical_t` | float | Karar eşiği Student's $t$ değeri ($t_{crit}$) |
| **Degrees of freedom** | `df` | integer | $df = N - 1$ |
| **Total sample size** | `n_total` | integer | Gereken minimal toplam eşleşmiş çift sayısı ($N$) |
| **Actual power** | `actual_power` | float | Tam sayı $N$ ile ulaşılan gerçek güç |

### 3.2. post-hoc Modu Çıktısı
| Çıktı Değişkeni | Anahtar Adı | Tip | Tanım |
|---|---|---|---|
| **Noncentrality parameter $\delta$** | `ncp` | float | $\delta = d_z \cdot \sqrt{N}$ |
| **Critical t** | `critical_t` | float | Karar eşiği Student's $t$ değeri ($t_{crit}$) |
| **Degrees of freedom** | `df` | integer | $df = N - 1$ |
| **Power** | `power` | float | Verilen $N$ ile ulaşılan güç |
| **Total sample size** | `n_total` | integer | Girdi olarak verilen çift sayısı |

---

## 4. Matematiksel Formülasyon ve Algoritma

### 4.1. Serbestlik Derecesi ve Noncentrality
$$df = N - 1$$
$$\delta = d_z \cdot \sqrt{N} \quad (\text{ncp})$$

### 4.2. Kritik $t$ ($t_{crit}$) Hesabı
Kuyruk başına olasılık $\alpha_{tail}$: çift yönlü için $\alpha/2$, tek yönlü için $\alpha$.

$$t_{crit} = Q_t(1 - \alpha_{tail},\, df) = Q_t^{\text{üst}}(\alpha_{tail},\, df)$$

* **Çift Yönlü (`two-tailed` / `2`):** $\alpha_{tail} = \alpha/2$
* **Tek Yönlü (`one-tailed` / `1`):** $\alpha_{tail} = \alpha$

> **Uygulama zorunluluğu:** $t_{crit}$, **üst kuyruk (survival) ters fonksiyonuyla** hesaplanmalıdır (örn. `scipy.stats.t.isf(alpha_tail, df)`). $p = 1 - \alpha_{tail}$ üretip alt kuyruk kuantil fonksiyonuna (`t.ppf`) vermek, küçük $\alpha$'da kayan nokta yuvarlamasından dolayı hassasiyet kaybettirir: $\alpha_{tail} = 5\times10^{-16}$ ve $df = 100$ için `ppf` yaklaşık 9.52, doğru değer yaklaşık 9.54 üretir; $\alpha_{tail} \lesssim 10^{-17}$ için `ppf` sonsuz döner. $t_{crit}$ sonlu değilse motor `RuntimeError: Power computation failed` fırlatır.

### 4.3. Güç (Power) Hesabı
* **Çift Yönlü:**
  $$\text{Power} = 1 - F_{nct}(t_{crit};\, df,\, \delta) + F_{nct}(-t_{crit};\, df,\, \delta)$$
* **Tek Yönlü:**
  $$\text{Power} = 1 - F_{nct}(t_{crit};\, df,\, \delta)$$

### 4.4. Analiz Algoritmaları

#### A. A-Priori Modu (Örneklem Büyüklüğü $N$ Arama Algoritması)
**Referans algoritma (doğrusal artım):**
1. $N = 2$ olarak başlat. Üst arama sınırı $N_{\max} = 100\,000$'dir.
2. $df = N - 1$ ve $\delta = d_z \cdot \sqrt{N}$ hesapla.
3. $t_{crit}$ değerini (Bölüm 4.2) hesapla.
4. $F_{nct}$ üzerinden mevcut gücü (`current_power`) hesapla.
5. $\text{current\_power} \ge \text{target\_power}$ ise dur ve değerleri döndür.
6. $N = N_{\max}$ adımında da hedef güce ulaşılamazsa dur ve `RuntimeError: Sample size exceeded maximum threshold` fırlat.
7. Değilse $N = N + 1$ yap ve 2. adıma dön.

**İzin verilen optimizasyon:** Aynı minimal tam sayı $N$'i garanti etmek şartıyla üstel sıçramalı arama + ikili arama ($O(\log N)$) kullanılabilir. Bu, güç fonksiyonunun $N$'e göre **zayıf monoton artan** (non-decreasing) olduğu varsayımına dayanır. Güç yüksek $N$'de kayan nokta hassasiyetinde 1.0'a doyabilir; bu nedenle monotonluk "kesin" değil "zayıf" olarak tanımlanır.

**Monotonluk güvencesi (kanıt değil, test):** Matematiksel kanıt bu spesifikasyonda verilmemiştir. Güvence şu testlerle sağlanır: (i) birkaç $(d_z,\alpha,\text{tails})$ ayarı için $N = 2 \dots 600$ taramasında güç değerlerinin sonlu olması ve $p_{N+1} \ge p_N - 10^{-9}$ sağlanması; (ii) birkaç ayar için optimize aramanın referans doğrusal aramayla aynı $N$'i üretmesi. Bu güvence yalnızca Bölüm 4.5'teki NaN kuralına uyulursa geçerlidir.

#### B. Post-Hoc Modu (Ulaşılan Güç Hesabı)
1. Girdi olarak verilen $N$ (`n_total`) için $df = N - 1$ ve $\delta = d_z \cdot \sqrt{N}$ hesapla.
2. İlgili yön (`tails`) ve $\alpha$ için $t_{crit}$ değerini (Bölüm 4.2) hesapla.
3. Bölüm 4.3'teki formülle doğrudan `power` değerini elde et ve sonuç sözlüğünü döndür.

### 4.5. Sayısal Uygulama Notu: `NaN` Dönen Merkezi Olmayan $t$ CDF'i
Bazı kütüphane sürümlerinde merkezi olmayan $t$ CDF'i ($F_{nct}$), matematiksel olarak geçerli girdilerde `NaN` döndürebilir. NaN bölgesi **sürüme bağlıdır ve geniştir**. Gözlem: scipy 1.18.1'de ham `nct.cdf`, $d_z = 0.5$, $\alpha = 0.05$ için güç $\approx 1$ olan $N \gtrsim 266$ değerlerinde bile `NaN` üretir. Başka sürümlerde bölge farklı olabilir ve sürüm bağımlılığı gelecekte değişebilir.

* `NaN` bir güç değeri **değildir**; `NaN >= target_power` karşılaştırmasının "güç yetersiz" sonucuna düşmesine izin verilmemelidir. Bu, doğrusal aramada bile gerçek değerden büyük $N$ üretir, üstel/ikili aramada ise çok daha büyük sapmalara yol açabilir.
* Bir $F_{nct}$ değeri sonlu değilse, aynı değer **sayısal integrasyonla** hesaplanmalıdır:
  $$F_{nct}(x;\, df,\, \delta) = \int_0^{\infty} \Phi\!\left(x\sqrt{\tfrac{v}{df}} - \delta\right) f_{\chi^2_{df}}(v)\, dv$$
  Burada $\Phi$ standart normal CDF'i, $f_{\chi^2_{df}}$ ise $df$ serbestlik dereceli ki-kare yoğunluğudur. İntegrasyon sınırları için $\chi^2_{df}$'nin $10^{-14}$ ve $1 - 10^{-14}$ kuantilleri kullanılabilir.
* Yedek yöntem de sonlu bir değer üretemezse motor `RuntimeError: Power computation failed` fırlatmalıdır (sessizce yanlış $N$ döndürmek yerine).
* Bölüm 5'teki V-16…V-20 ve V-33/V-34 vektörleri bu bölgeleri ve küçük-$\alpha$ rejimini kapsar; doğrulama değerleri `nct.cdf`'ten bağımsız integrasyonla üretilmiştir.

---

## 5. Doğrulama Vektörleri (34 Adet Referans Vektörü + 3 Determine + 29 Negatif)

**Kaynak notu:** Bu bölümdeki tüm sayısal değerler `nct.cdf`'ten **bağımsız** sayısal integrasyonla (Bölüm 4.5'teki integral, kesin $t_{crit}$ için `t.isf`) üretilmiş ve minimal $N$ için hem $N$ (güç $\ge$ hedef) hem $N-1$ (güç $<$ hedef) doğrulanmıştır. Değerler G*Power arayüzünde **elle teyit edilmemiştir**; bu teyit yapılana kadar kaynak etiketi "bağımsız sayısal integrasyon"dur, "G*Power protokol kaydı" değildir.

### 5.1. A-Priori Doğrulama Vektörleri (V-01 .. V-21, V-33, V-34)
Tails sütununda `2` çift yönlü, `1` tek yönlü anlamına gelir.

| No | Tails | $d_z$ | $\alpha$ | Target Power | Beklenen $N$ | Beklenen $df$ | Beklenen $\delta$ | Beklenen $t_{crit}$ | Beklenen Power |
|---|---|---|---|---|---|---|---|---|---|
| **V-01** | 2 | 0.5 | 0.05 | 0.80 | **34** | 33 | 2.915476 | 2.034515 | 0.807778 |
| **V-02** | 2 | 0.2 | 0.05 | 0.80 | **199** | 198 | 2.821347 | 1.972017 | 0.801691 |
| **V-03** | 2 | 0.8 | 0.05 | 0.80 | **15** | 14 | 3.098387 | 2.144787 | 0.821311 |
| **V-04** | 2 | 0.5 | 0.05 | 0.90 | **44** | 43 | 3.316625 | 2.016692 | 0.900031 |
| **V-05** | 2 | 0.5 | 0.05 | 0.95 | **54** | 53 | 3.674235 | 2.005746 | 0.950212 |
| **V-06** | 2 | 0.8 | 0.05 | 0.95 | **23** | 22 | 3.836665 | 2.073873 | 0.955850 |
| **V-07** | 2 | 0.3 | 0.01 | 0.90 | **169** | 168 | 3.900000 | 2.605410 | 0.900699 |
| **V-08** | 2 | 0.4 | 0.01 | 0.95 | **115** | 114 | 4.289522 | 2.619645 | 0.950622 |
| **V-09** | 1 | 0.5 | 0.05 | 0.80 | **27** | 26 | 2.598076 | 1.705618 | 0.811832 |
| **V-10** | 1 | 0.2 | 0.05 | 0.80 | **156** | 155 | 2.497999 | 1.654744 | 0.800167 |
| **V-11** | 1 | 0.8 | 0.05 | 0.80 | **12** | 11 | 2.771281 | 1.795885 | 0.828981 |
| **V-12** | 1 | 0.5 | 0.01 | 0.90 | **55** | 54 | 3.708099 | 2.397410 | 0.901121 |
| **V-13** | 1 | 0.5 | 0.05 | 0.95 | **45** | 44 | 3.354102 | 1.680230 | 0.951240 |
| **V-14** | 1 | 0.3 | 0.05 | 0.90 | **97** | 96 | 2.954657 | 1.660881 | 0.901280 |
| **V-15** | 1 | 0.4 | 0.01 | 0.80 | **66** | 65 | 3.249615 | 2.385097 | 0.803798 |
| **V-16** | 2 | 0.3 | 0.001 | 0.95 | **277** | 276 | 4.992995 | 3.326125 | 0.950873 |
| **V-17** | 2 | 0.3 | 0.001 | 0.99 | **356** | 355 | 5.660389 | 3.318143 | 0.990006 |
| **V-18** | 2 | 0.5 | 0.001 | 0.999 | **169** | 168 | 6.500000 | 3.349379 | 0.999045 |
| **V-19** | 2 | 0.1 | 0.001 | 0.99 | **3161** | 3160 | 5.622277 | 3.293608 | 0.990016 |
| **V-20** | 2 | 0.05 | 0.001 | 0.90 | **8367** | 8366 | 4.573565 | 3.291690 | 0.900001 |
| **V-21** | 2 | 20.0 | 0.05 | 0.80 | **2** | 1 | 28.284271 | 12.706205 | 0.973524 |
| **V-33** | 2 | 0.5 | 1e-10 | 0.90 | **261** | 260 | 8.077747 | 6.742856 | 0.900823 |
| **V-34** | 2 | 1.0 | 1e-15 | 0.90 | **117** | 116 | 10.816654 | 9.306772 | 0.904018 |

V-16…V-20, `NaN` dönen $F_{nct}$ bölgelerini ve küçük-$\alpha$ rejimini (Bölüm 4.5) sınayan regresyon vektörleridir. V-21'de $N = 2$ (alt sınır) yeterlidir. V-33 ve V-34, $t_{crit}$'in `isf` ile hesaplanmasını sınar. Ölçülen: V-34'te (`df = 116`) `t.ppf(1 - α/2, df)` $t_{crit}$'i yaklaşık 0.019 düşük verir (tolerans $10^{-5}$ aşılır); V-33'te fark yaklaşık $1.4\times10^{-8}$'dir.

### 5.2. Post-Hoc Doğrulama Vektörleri (V-22 .. V-32)
| No | Tails | $d_z$ | $\alpha$ | $N$ (`n_total`) | Beklenen $df$ | Beklenen $\delta$ (`ncp`) | Beklenen $t_{crit}$ | Beklenen Power |
|---|---|---|---|---|---|---|---|---|
| **V-22** | 1 | 0.50 | 0.05 | 45 | 44 | 3.354102 | 1.680230 | 0.951240 |
| **V-23** | 2 | 0.35 | 0.05 | 40 | 39 | 2.213594 | 2.022691 | 0.578855 |
| **V-24** | 2 | 0.25 | 0.05 | 80 | 79 | 2.236068 | 1.990450 | 0.598282 |
| **V-25** | 2 | 0.60 | 0.01 | 25 | 24 | 3.000000 | 2.796940 | 0.585717 |
| **V-26** | 1 | 0.15 | 0.05 | 200 | 199 | 2.121320 | 1.652547 | 0.680553 |
| **V-27** | 2 | 0.45 | 0.05 | 60 | 59 | 3.485685 | 2.000995 | 0.929008 |
| **V-28** | 2 | 0.40 | 0.05 | 50 | 49 | 2.828427 | 2.009575 | 0.791787 |
| **V-29** | 2 | 0.60 | 0.01 | 20 | 19 | 2.683282 | 2.860935 | 0.450116 |
| **V-30** | 1 | 0.20 | 0.05 | 50 | 49 | 1.414214 | 1.676551 | 0.401222 |
| **V-31** | 2 | 0.70 | 0.05 | 30 | 29 | 3.834058 | 2.045230 | 0.959446 |
| **V-32** | 2 | 1.00 | 0.05 | 10 | 9 | 3.162278 | 2.262157 | 0.803097 |

Bu vektörlerin tamamı birbirinden bağımsız girdi kombinasyonlarıdır; $N$ hedef güce denk gelmediği için post-hoc gücün a-priori vektörlerden ayrı sınanmasını sağlar. ("Bağımsız" burada vektörlerin birbirini tekrar etmediği anlamındadır; test tasarımı eşleştirilmiş (bağımlı) örneklem testidir.)

### 5.3. Klinik Tansiyon & Determine Doğrulama Vektörleri
Tüm Determine vektörlerinde `tails = 'two-tailed'`, $\alpha = 0.05$, target power $= 0.80$ kullanılır.

| No | Girdiler | Türetilen $\sigma_D$ | Türetilen $d_z$ | Beklenen sonuç |
|---|---|---|---|---|
| **V-DET-01** (Farklar) | $\mu_D = 5.0,\ \sigma_D = 10.0$ | 10.0 | 0.5 | $N = 34$ (V-01 ile eşleşir) |
| **V-DET-02** (Gruplar) | $\mu_1 = 140,\ \mu_2 = 135,\ \sigma_1 = 10,\ \sigma_2 = 10,\ r = 0.5$ | 10.0 | 0.5 | $N = 34$ |
| **V-DET-03** (Çok küçük σ, göreli eşik) | $\mu_1 = 5\times10^{-7},\ \mu_2 = 0,\ \sigma_1 = \sigma_2 = 10^{-7},\ r = 0.5$ | $10^{-7}$ | 5.0 | $N = 3$, $df = 2$, $\delta = 8.660254$, $t_{crit} = 4.302653$, power $= 0.975462$ |

### 5.4. Negatif Test Vektörleri (Hata Senaryoları)
Aksi belirtilmedikçe geçerli taban girdi: `tails='two-tailed'`, $d_z = 0.5$, $\alpha = 0.05$, target power $= 0.80$. Beklenen hata türü ve mesajı birebir eşleşmelidir.

| No | Değişen girdi | Beklenen istisna |
|---|---|---|
| **E-01** | `tails = 'left'` | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-02** | $d_z = 0$ | `ValueError: Effect size must be strictly positive` |
| **E-03** | $d_z = -0.5$ | `ValueError: Effect size must be strictly positive` |
| **E-04** | $\alpha = 1.0$ | `ValueError: Alpha must be between 0 and 1` |
| **E-05** | target power $= 0$ | `ValueError: Target power must be between 0 and 1` |
| **E-06** | $d_z =$ `NaN` | `ValueError: Parameters cannot be NaN, Infinite or empty` |
| **E-07** | $d_z =$ `"0.5"` (string) | `TypeError: Numeric parameters must be int or float` |
| **E-08** | $d_z = 0.001$ | `RuntimeError: Sample size exceeded maximum threshold` |
| **E-09** | Determine/Farklar: $\mu_D = 0,\ \sigma_D = 10$ | `ValueError: Mean difference cannot be zero (no detectable effect)` |
| **E-10** | Determine/Farklar: $\mu_D = 5,\ \sigma_D = 0$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` |
| **E-11** | Determine/Farklar: $\mu_D = 5,\ \sigma_D = -1$ | `ValueError: Standard deviations must be strictly positive` |
| **E-12** | Determine/Gruplar: $\mu_1 - \mu_2 = 5,\ \sigma_1 = \sigma_2 = 10,\ r = 1.0$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` |
| **E-13** | Determine/Gruplar: aynı değerler, $r = 1.5$ | `ValueError: Correlation must be between -1 and 1` |
| **E-14** | Determine/Gruplar: $\sigma_1 = 0,\ \sigma_2 = 10,\ r = 0.5$ | `ValueError: Standard deviations must be strictly positive` |
| **E-15** | $d_z =$ `None`, $\alpha =$ `"x"` | `ValueError: Parameters cannot be NaN, Infinite or empty` |
| **E-16** | $d_z =$ `"x"`, $\alpha =$ `None` | `TypeError: Numeric parameters must be int or float` |
| **E-17** | Post-hoc: $N = 1$ (`n_total`) | `ValueError: Sample size (n_total) must be >= 2` |
| **E-18** | $d_z =$ `True` (bool) | `TypeError: Numeric parameters must be int or float` |
| **E-19** | $d_z =$ `inf` | `ValueError: Parameters cannot be NaN, Infinite or empty` |
| **E-20** | `tails = None` | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-21** | `tails = True` | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-22** | `tails = "1"` (string) | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-23** | `tails = 1.0` (float) | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` |
| **E-24** | Post-hoc: $N = 34.5$ | `TypeError: Sample size must be an integer` |
| **E-25** | Post-hoc: $N =$ `Fraction(69, 2)` | `TypeError: Sample size must be an integer` |
| **E-26** | Post-hoc: $N = 100\,001$ | `RuntimeError: Sample size exceeded maximum threshold` |
| **E-27** | Post-hoc: $d_z = 0,\ N = 1$ | `ValueError: Sample size (n_total) must be >= 2` (Adım 4, Adım 8'den önce) |
| **E-28** | Post-hoc: $N =$ `"34"` (string) | `TypeError: Numeric parameters must be int or float` |
| **E-29** | Post-hoc: $N =$ `None` | `ValueError: Parameters cannot be NaN, Infinite or empty` |

**Pozitif tür vektörleri:** `numpy.float64(0.5)` ve `numpy.int64(1)` ($d_z$) kabul edilir (a-priori sonuçlar sırasıyla $N = 34$ ve $N = 10$). Post-hoc'ta $d_z = 0.5$, $\alpha = 0.05$, çift yönlü için `n_total` olarak `34`, `34.0`, `numpy.int64(34)` ve `Fraction(68, 2)` aynı sonucu (V-23'ün eşdeğeri: $N = 34$, power $= 0.807778$) üretir. `tails` için `numpy.int64(1)` / `numpy.int64(2)` kabul edilir.

### 5.5. Tolerans Kuralı
* $N$, $df$ ve $n\_total$ için **tam eşitlik** aranır.
* $\delta$ (`ncp`), $t_{crit}$, $\text{actual\_power}$ ve $\text{power}$ için mutlak tolerans $\vert a - b\vert \le 10^{-5}$ kabul edilir.

---

## 6. Uç Durumlar ve Hata Yönetimi Hiyerarşisi

Doğrulamalar **aşağıdaki sırayla** yapılır; ilk başarısız kontrol hatayı belirler ve sonrakiler çalıştırılmaz. Böylece aynı girdi birden fazla kuralı ihlal ettiğinde sonuç deterministik olur.

| Sıra | Kontrol | Fırlatılan İstisna | CONTRACT.md Code |
|---|---|---|---|
| 1 | Sayısal girdilerin parametre bazında denetimi: `None` → `ValueError`; `numbers.Real` değil veya `bool` → `TypeError`; `NaN` / `inf` / `-inf` → `ValueError` | `ValueError: Parameters cannot be NaN, Infinite or empty` / `TypeError: Numeric parameters must be int or float` | `INVALID_VALUE` |
| 2 | `tails` değeri `'one-tailed'`, `'two-tailed'`, `1`, `2` dışında (`bool`, `None`, `"1"`, `1.0` dahil) | `ValueError: Tails must be 'one-tailed' or 'two-tailed'` | `OUT_OF_RANGE` |
| 3 | *(post-hoc)* $N$ tam sayı değerli değil | `TypeError: Sample size must be an integer` | `INVALID_VALUE` |
| 4 | *(post-hoc)* $N < 2$ | `ValueError: Sample size (n_total) must be >= 2` | `OUT_OF_RANGE` |
| 5 | *(post-hoc)* $N > 100\,000$ | `RuntimeError: Sample size exceeded maximum threshold` | `NO_SOLUTION` |
| 6 | $\alpha \le 0$ veya $\alpha \ge 1$ | `ValueError: Alpha must be between 0 and 1` | `OUT_OF_RANGE` |
| 7 | *(a-priori)* $\text{target\_power} \le 0$ veya $\ge 1$ | `ValueError: Target power must be between 0 and 1` | `OUT_OF_RANGE` |
| 8 | $d_z \le 0$ (doğrudan girilen veya türetilen) | `ValueError: Effect size must be strictly positive` | `OUT_OF_RANGE` |
| 9 | *(Gruplar)* $r < -1$ veya $r > 1$ | `ValueError: Correlation must be between -1 and 1` | `OUT_OF_RANGE` |
| 10 | *(Gruplar)* $\sigma_1 \le 0$ veya $\sigma_2 \le 0$; *(Farklar)* $\sigma_D < 0$ | `ValueError: Standard deviations must be strictly positive` | `OUT_OF_RANGE` |
| 11 | *(Farklar)* $\sigma_D = 0$; *(Gruplar)* $\text{radicand} \le 10^{-12} \cdot (\sigma_1^2 + \sigma_2^2)$ | `ZeroDivisionError: Standard deviation of difference cannot be zero` | `INVALID_VALUE` |
| 12 | *(Determine)* $\mu_D = 0$ veya $\vert\mu_1 - \mu_2\vert = 0$ | `ValueError: Mean difference cannot be zero (no detectable effect)` | `INCONSISTENT` |
| 13 | *(a-priori)* $N = N_{\max}$ ($100\,000$) değerinde de hedef güce ulaşılamadı | `RuntimeError: Sample size exceeded maximum threshold` | `NO_SOLUTION` |
| 14 | *(hesap sırasında)* $t_{crit}$ veya güç sonlu değil, yedek integrasyon da sonuç veremedi | `RuntimeError: Power computation failed` | `NO_SOLUTION` |

**Notlar:**
* **Adım 1'in parametre sırası:** Parametreler **imzadaki sırayla** işlenir ve her parametre kendi içinde şu sırayla denetlenir: `None` → tür/`bool` → `NaN`/`inf`. İlk geçersiz parametre hatayı belirler. İmzalar:
  * `power_matched_pairs(effect_size_dz, alpha, target_power, tails)`
  * `post_hoc_matched_pairs(effect_size_dz, n_total, alpha, tails)`
  * `calculate_dz_from_differences(mean_diff, sd_diff)`
  * `calculate_dz_from_groups(mean1, mean2, sd1, sd2, correlation)`
* `tails` sayısal doğrulamaya (Adım 1) dahil değildir; kendi kuralı Adım 2'dedir. Bu yüzden `tails=None` Adım 1'in "None" hatasını değil, Adım 2'nin tails hatasını verir.
* **Determine ile analiz sırası:** Determine fonksiyonları (Adım 9-12 ve kendi Adım 1 denetimi) analiz fonksiyonlarından önce ayrı çağrılır; türetilen $d_z$ analiz fonksiyonuna girdi olarak verilir ve Adım 1-8 orada işletilir.
* Sıfıra bölme durumları tek bir türde toplanmıştır: $\sigma_D$'nin tam sıfır (veya göreli eşik altında) olması her zaman `ZeroDivisionError` verir; negatif standart sapma `ValueError` verir.
* CLI ve servis katmanında hatalar `{"error": "<mesaj>", "code": "<KOD>", "field": "<alan>"}` formatına dönüştürülür. `field`, hatayı üreten parametrenin değişken adıdır (örn. `alpha`, `n_total`).

---

## 7. Açık Noktalar (Bu spesifikasyonla kapatılamayanlar)
* `code` değerlerinin (`INVALID_VALUE`, `OUT_OF_RANGE`, `NO_SOLUTION`, `INCONSISTENT`) tamamı ve `TypeError` / `Power computation failed` için doğru kod `CONTRACT.md` ile birebir doğrulanmalıdır; yukarıdaki eşleme bu doküman hazırlanırken CONTRACT.md görülmeden yapılmıştır.
* Determine modülünün CLI bayrakları (`--mean-diff`, `--sd-diff` vb.) ve mod seçimi (a-priori / post-hoc) `CONTRACT.md` içinde tanımlıdır; bu spesifikasyon yalnızca fonksiyon düzeyindeki davranışı tanımlar.
* Bölüm 5 vektörlerinin G*Power 3.1.9.7 arayüzünde elle teyidi yapılmamıştır (Bölüm 5 kaynak notuna bakın).