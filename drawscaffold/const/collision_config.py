
# Collision Detection and Resolution Configuration

# Güvenlik Kontrolü Eşik Değeri
# Bu değer, iki iskele hattı arasındaki minimum güvenli mesafeyi belirler.
# threshold değerini arttırmak çarpışma riskini/güvenlik payını arttırır ancak iskelelerin sığmasını zorlaştırabilir.
# Default: 40.0
# Önceki ayarlar: 10.0, 20.0, 40.0
SAFETY_THRESHOLD = 40.0

# Kritik Kısa Duvar Uzunluğu
# Bir duvarın "çok kısa" olarak sınıflandırılması için gereken maksimum uzunluk (cm).
# Bu değerin altındaki duvarlar için daha düşük bir güvenlik payı (buffer) uygulanır.
# len_a veya len_b bu değerden küçükse "criminally_short" kabul edilir.
# Default: 300
# Çarpışma olmaması için 250 yapın. Boş duvar kalmaması için arttırın (örn 350).
CRITICAL_SHORT_DISTANCE = 300

# Kısa Duvarlar İçin Güvenlik Payı (Buffer)
# "Critical Short" olarak işaretlenen duvarlar için uygulanan köşe tampon mesafesi (cm).
# Bu değer ne kadar küçükse, kısa duvarlar o kadar dar alanlara sığabilir, ancak iç içe geçme riski artar.
# Default: 20
SHORT_WALL_BUFFER = 20

# Normal Duvarlar İçin Güvenlik Payı (Buffer)
# Normal uzunluktaki duvarlar için standart köşe tampon mesafesi (cm).
# Default: 70
NORMAL_WALL_BUFFER = 70
