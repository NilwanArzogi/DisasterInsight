# Laporan Uji Konsistensi Data Agregat vs Data Kejadian

Dibuat otomatis oleh `backend/pipeline/check_consistency.py`.

## Cakupan kode kabupaten
- Kode di data kejadian yang tidak ada di file agregat: 0 kode (0 kejadian)
- Kode di file agregat tanpa satu pun kejadian banjir/longsor/karhutla: 12

## Pasangan kabupaten-tahun yang melanggar aturan
- Total pasangan diuji: 3060
- Pelanggaran (3 jenis > agregat): 25

## Porsi tiga jenis terhadap total semua jenis, per tahun
```
       agregat  tiga_jenis  porsi_tiga_jenis_%
tahun                                         
2018      3449        1988                57.6
2019      3847        2269                59.0
2020      4714        3350                71.1
2021      5453        4181                76.7
2022      3595        2529                70.3
2023      5519        4020                72.8
```

## Pelanggaran terbesar (20 teratas)
```
kode_kabupaten      nama_kabupaten  tahun  jumlah_semua_jenis  tiga_jenis  selisih
          3201               BOGOR   2021                 387         418      -31
          3202            SUKABUMI   2021                 157         174      -17
          3211            SUMEDANG   2021                  56          63       -7
          3208            KUNINGAN   2021                  27          33       -6
          3217       BANDUNG BARAT   2021                  44          48       -4
          6501            BULUNGAN   2021                  14          18       -4
          6571        KOTA TARAKAN   2021                  28          31       -3
          3211            SUMEDANG   2019                  36          38       -2
          6372     KOTA BANJARBARU   2020                  28          30       -2
          1804       LAMPUNG BARAT   2020                   4           6       -2
          7211        BANGGAI LAUT   2021                   6           8       -2
          1472          KOTA DUMAI   2021                   6           7       -1
          1302               SOLOK   2020                  14          15       -1
          7202                POSO   2020                   3           4       -1
          6205        BARITO UTARA   2020                   8           9       -1
          6106         KAPUAS HULU   2020                   8           9       -1
          3273        KOTA BANDUNG   2021                   4           5       -1
          2172 KOTA TANJUNG PINANG   2021                  35          36       -1
          7271           KOTA PALU   2021                   6           7       -1
          1402      INDRAGIRI HULU   2022                   6           7       -1
```
