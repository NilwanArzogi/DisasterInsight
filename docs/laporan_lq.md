# Laporan Hasil LQ (2018-2023)

Dibuat otomatis oleh `backend/pipeline/run_lq.py`.

## Validasi independen
```
[LULUS] Jumlah BANJIR = jumlah baris data bersih (8020 vs 8020)
[LULUS] Jumlah TANAH LONGSOR = jumlah baris data bersih (5433 vs 5433)
[LULUS] Jumlah KEBAKARAN HUTAN DAN LAHAN = jumlah baris data bersih (4884 vs 4884)
[LULUS] E(nasional,semua) = jumlah E(i,semua) (26671 vs 26671)
[LULUS] Rata-rata LQ berbobot BANJIR = 1 (1.000000000000)
[LULUS] Rata-rata LQ berbobot TANAH LONGSOR = 1 (1.000000000000)
[LULUS] Rata-rata LQ berbobot KEBAKARAN HUTAN DAN LAHAN = 1 (1.000000000000)
[LULUS] Tidak ada LQ negatif
[LULUS] Tidak ada pembilang melebihi penyebut
```

## Status per jenis bencana
```
status                      ok  tidak_ada_laporan  tidak_dapat_dihitung
jenis_bencana                                                          
BANJIR                     489                 16                     5
KEBAKARAN HUTAN DAN LAHAN  325                180                     5
TANAH LONGSOR              347                158                     5
```

## Kategori per jenis bencana
```
kategori                   LQ < 1  LQ > 1  tidak ada laporan  tidak dapat dihitung
jenis_bencana                                                                     
BANJIR                        187     302                 16                     5
KEBAKARAN HUTAN DAN LAHAN     174     151                180                     5
TANAH LONGSOR                 243     104                158                     5
```

## Kabupaten dengan data sedikit (total kejadian < 10)
```
jenis_bencana
BANJIR                       90
KEBAKARAN HUTAN DAN LAHAN    90
TANAH LONGSOR                90
```

## Sensitivitas satuan hitung (baris vs kombinasi unik kabupaten-tanggal-jenis)
```
                    jenis  kabupaten_dibandingkan  korelasi_peringkat  ganti_kategori  lintas_batas_1
                   BANJIR                     505               0.998               4               4
KEBAKARAN HUTAN DAN LAHAN                     505               1.000               4               4
            TANAH LONGSOR                     505               1.000              11              11
```

## Pemeriksaan manual satu kabupaten
```
BOGOR (3201), TANAH LONGSOR
  E(i,k)=723  E(i,semua)=1349  E(nasional,k)=5433  E(nasional,semua)=26671
  LQ = (723/1349) / (5433/26671) = 2.6310  [LQ > 1]
```
