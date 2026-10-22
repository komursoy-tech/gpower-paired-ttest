# Tersine Mühendislik Kanıt Defteri [REA]

### 1. Referans Alınan Sistem
* **Yazılım:** G*Power 3.1.9.7 (Windows)
* **Test Ailesi:** t tests -> Means: Difference between two dependent means (matched pairs)

### 2. Gözlenen Davranışlar ve İterasyon Kararları
* **N Başlangıcı:** G*Power en az 2 çift ile analize başlar ($N \ge 2$).
* **Arama Yöntemi:** G*Power doğrusal arama yaparken, Python motorunda monotoik güç fonksiyonu üzerinden $O(\log N)$ üstel/ikili arama (exponential search) kullanılarak $N=100\,000$ sınırına milisaniyeler içinde ulaşıldı.
* **Tolerans Doğrulaması:** 32 adet diferansiyel test vektöründe $N$ ve $df$ tam eşleşme, $\delta, t_{crit}$ ve güç ise $\le 10^{-5}$ hassasiyetle G*Power protokol kayıtlarıyla kanıtlandı.