# DrawScaffold - Sistem Dokümantasyonu

**Versiyon:** 2.0  
**Son Güncelleme:** 29 Ocak 2026

---

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [İskele Oluşturma Süreci](#iskele-oluşturma-süreci)
3. [Kullanım Kılavuzu](#kullanım-kılavuzu)
4. [Komut Referansı](#komut-referansı)
5. [Çıktı Formatları](#çıktı-formatları)
6. [Örnekler](#örnekler)

---

## Genel Bakış

DrawScaffold, bina cephelerine göre otomatik iskele yerleşimi hesaplayan ve görselleştiren bir sistemdir.

### Temel Özellikler

- 🏗️ Otomatik iskele modül yerleşimi (250cm ve 150cm modüller)
- 📐 Girinti (inset) ve çıkıntı (outset) desteği
- 🔄 Köşe ayarlaması (adjust-corners)
- 📊 Malzeme listesi hesaplama
- 🖼️ PNG, SVG ve DXF çıktı formatları

---

## İskele Oluşturma Süreci

### 1. Duvar Tanımı

Sistem dört ana cepheyi işler:
- **F (Front):** Ön cephe (+X yönünde)
- **R (Right):** Sağ cephe (+Y yönünde)
- **B (Back):** Arka cephe (-X yönünde)
- **L (Left):** Sol cephe (-Y yönünde)

```
        B (Back)
    ┌─────────────┐
    │             │
L   │   BİNA      │   R
    │             │
    └─────────────┘
        F (Front)
```

### 2. Modül Yerleşimi

Sistem her cephe için:

1. **Toplam uzunluğu alır** (örn: 2000cm)
2. **250cm modüller yerleştirir** (öncelikli)
3. **Kalan boşluğa 150cm modüller yerleştirir**
4. **Küçük boşluklar bırakır** (eğer --no-150 aktifse)

```
Örnek: 800cm duvar
├── 250cm ──┼── 250cm ──┼── 250cm ──┼─ 50cm boşluk ─┤
```

### 3. Gap (Boşluk) Hesabı

İskeleler duvardan **25cm** mesafede yerleştirilir:

```
    ┌─────────────┐
    │    DUVAR    │
    └─────────────┘
          ↕ 25cm gap
    ╔═════════════╗
    ║   İSKELE   ║
    ╚═════════════╝
```

### 4. Girinti ve Çıkıntı (Inset/Outset)

#### Inset (Girinti)
Duvar belirli bir noktadan içeri çekilir:

```
Önce:           Sonra (inset 300cm derinlikte):
────────────    ────────┐
                        │ 300cm
                ────────┘
```

#### Outset (Çıkıntı)
Duvar belirli bir noktadan dışarı çıkar:

```
Önce:           Sonra (outset 300cm derinlikte):
────────────    ────────┘
                        │ 300cm
                ────────┐
```

### 5. Köşe Ayarlaması (--adjust-corners)

Komşu duvarlardaki çıkıntılar göz önüne alınarak duvar uzunlukları ayarlanır:

```
Outset olmadan:          Outset ile (adjust-corners):
┌───────┐                ┌───────┐
│       │                │       ├──┐
│       │                │       │  │ R duvarı kısa
└───────┘                └───────┴──┘
```

---

## Kullanım Kılavuzu

### Hızlı Başlangıç

```bash
# 1. Projeye git
cd c:\path\to\drawscaffold

# 2. Basit dikdörtgen bina
poetry run python top_down_main.py \
  --wall F:2000 --wall R:1500 --wall B:2000 --wall L:1500 \
  --height-in-cm 1500 \
  --image \
  --project-name my_building
```

### Adım Adım Kullanım

#### Adım 1: Duvarları Tanımla

Her duvar için `--wall SIDE:LENGTH` kullan:

```bash
--wall F:2000   # Ön cephe 2000cm (20m)
--wall R:1500   # Sağ cephe 1500cm (15m)
--wall B:2000   # Arka cephe 2000cm
--wall L:1500   # Sol cephe 1500cm
```

#### Adım 2: Özellikleri Ekle (Opsiyonel)

Girinti veya çıkıntı için `--feature SIDE:type,position,depth`:

```bash
--feature F:inset,500,300    # Ön cephede 500cm'de 300cm içeri girinti
--feature R:outset,300,250   # Sağ cephede 300cm'de 250cm dışarı çıkıntı
```

#### Adım 3: Yükseklik ve Eğim

```bash
--height-in-cm 1500    # İskele yüksekliği 1500cm (15m)
--surface-slope 15     # 15 derece eğimli yüzey (çatı için)
```

#### Adım 4: Çıktı Formatı

```bash
--image         # PNG görüntüsü
--svg           # SVG vektör
--dxf           # AutoCAD DXF
```

---

## Komut Referansı

### Temel Argümanlar

| Argüman | Kısa | Zorunlu | Açıklama |
|---------|------|---------|----------|
| `--wall SIDE:LENGTH` | | Evet | Duvar tanımı |
| `--height-in-cm N` | | Evet | İskele yüksekliği (cm) |
| `--project-name NAME` | | Hayır | Proje adı |

### Özellik Argümanları

| Argüman | Açıklama |
|---------|----------|
| `--feature SIDE:type,pos,depth` | Girinti/çıkıntı ekle |
| `--adjust-corners` | Köşe ayarlaması aktif |
| `--no-150` | 150cm modül kullanma |

### Çıktı Argümanları

| Argüman | Açıklama |
|---------|----------|
| `--image` | PNG çıktısı |
| `--svg` | SVG vektör çıktısı |
| `--dxf` | DXF CAD çıktısı |

### Gelişmiş Argümanlar

| Argüman | Varsayılan | Açıklama |
|---------|------------|----------|
| `--surface-slope N` | 0 | Yüzey eğimi (derece) |
| `--toe-board` | True | Ayak tahtası |
| `--verbose` | False | Detaylı çıktı |

---

## Çıktı Formatları

### Klasör Yapısı

Çıktılar `manual_output/YYYY_MM_DD_HH_MM_SS/` altına kaydedilir:

```
manual_output/
└── 2026_01_29_00_00_00/
    ├── my_building.png      # Görüntü
    ├── my_building.svg      # Vektör
    ├── my_building.dxf      # CAD
    └── materials.json       # Malzeme listesi
```

### Malzeme Çıktısı (JSON)

```json
{
  "FOOT_STD": 28,
  "PLATFORM_250": 140,
  "PLATFORM_150": 28,
  "SUPPORT_250": 140,
  "DIAGONAL": 24,
  "tie": 28,
  "SIGN_": 168
}
```

---

## Örnekler

### Örnek 1: Basit Dikdörtgen Bina

```bash
poetry run python top_down_main.py \
  --wall F:2000 --wall R:1500 --wall B:2000 --wall L:1500 \
  --height-in-cm 1000 \
  --image \
  --project-name simple_building
```

### Örnek 2: Girintili Bina

```bash
poetry run python top_down_main.py \
  --wall F:3000 --wall R:2000 --wall B:3000 --wall L:2000 \
  --feature F:inset,1000,500 \
  --feature B:inset,1500,500 \
  --height-in-cm 1500 \
  --image \
  --project-name inset_building
```

### Örnek 3: Çıkıntılı Bina (Balkon)

```bash
poetry run python top_down_main.py \
  --wall F:2500 --wall R:1800 --wall B:2500 --wall L:1800 \
  --feature F:outset,800,300 \
  --feature F:outset,1700,300 \
  --height-in-cm 1200 \
  --adjust-corners \
  --image \
  --project-name balcony_building
```

### Örnek 4: 150cm Modülsüz (Boşluk Tercihli)

```bash
poetry run python top_down_main.py \
  --wall F:1800 --wall R:1200 --wall B:1800 --wall L:1200 \
  --height-in-cm 900 \
  --no-150 \
  --image \
  --project-name gaps_preferred
```

### Örnek 5: Eğimli Yüzey (Çatı)

```bash
poetry run python top_down_main.py \
  --wall F:2000 --wall R:1500 --wall B:2000 --wall L:1500 \
  --height-in-cm 1500 \
  --surface-slope 20 \
  --image \
  --project-name sloped_roof
```

---

## Eski Format (Legacy)

Geriye uyumluluk için eski format hala destekleniyor:

```bash
poetry run python top_down_main.py \
  --facade "flat,0,2000,0,F" \
  --facade "inset,500,2000,300,F" \
  --facade "flat,0,1500,0,R" \
  --height-in-cm 1500 \
  --image
```

**Format:** `type,position,length,depth,side`

---

## Sorun Giderme

### Sık Karşılaşılan Hatalar

| Hata | Çözüm |
|------|-------|
| "No walls defined" | En az bir `--wall` argümanı ekle |
| "Invalid side" | F, R, B, L harflerinden birini kullan |
| Boş görüntü | Yüksekliği kontrol et (`--height-in-cm`) |

