# Laporan Kualitas Data Kejadian (2018-2023)

Dibuat otomatis oleh `backend/pipeline/clean_events.py`.

## Ringkasan per jenis bencana
```
                           dimuat  dalam_periode  identik_dihapus  tersisa  ditandai_ganda
BANJIR                      11898           8052               32     8020             438
KEBAKARAN HUTAN DAN LAHAN    6257           4921               37     4884             177
TANAH LONGSOR                7681           5518               85     5433             967
```

## Jumlah kejadian per tahun (setelah pembersihan)
```
jenis_bencana  BANJIR  KEBAKARAN HUTAN DAN LAHAN  TANAH LONGSOR
tahun                                                          
2018              869                        511            608
2019              790                        753            726
2020             1609                        612           1129
2021             1915                        585           1681
2022             1573                        272            684
2023             1264                       2151            605
```

## Wilayah
- Kode kabupaten unik: 498
- Nilai provinsi unik: 37
- Kode kabupaten dengan lebih dari satu ejaan nama: 21
- Baris dengan kode lama Papua yang dipadankan ke kode baru: 32

## Aturan yang diterapkan
- Periode: 2018-01-01 sampai 2023-12-31
- Kode lama Papua dipadankan ke kode baru (backend/reference/crosswalk_kode.csv)
- Baris identik penuh (kabupaten, tanggal, jenis, lokasi, penyebab) dihapus
- Baris dengan kabupaten, tanggal, dan jenis sama ditandai, tidak dihapus
- Provinsi dinormalisasi: DAERAH ISTIMEWA YOGYAKARTA -> DI YOGYAKARTA, P A P U A -> PAPUA
