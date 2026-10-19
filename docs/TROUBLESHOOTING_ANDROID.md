# Panduan Pemecahan Masalah Instalasi Android (Troubleshooting Guide)

Dokumen ini menyediakan panduan langkah-demi-langkah untuk mengatasi kendala pemasangan (*sideload APK*) aplikasi **Tatap** pada perangkat Android (khususnya Samsung Galaxy dengan antarmuka One UI, Xiaomi/HyperOS, Infinix/XOS, Oppo/Realme, dan Google Pixel).

---

## 1. Kendala Khusus Perangkat Samsung Galaxy (One UI 6.0 / 6.1 / 7.0 / 8.0)

Pada pembaruan Samsung One UI versi terbaru (Android 14 ke atas), Samsung mengaktifkan fitur keamanan bawaan bernama **Pemblokir Otomatis (Auto Blocker)** secara *default*. Fitur ini memblokir seluruh pemasangan aplikasi dari luar toko resmi (*Galaxy Store / Play Store*), sehingga memicu dialog error:
> *"Pemasangan diblokir. Pemblokir Otomatis menghentikan pemasangan aplikasi dari sumber tidak resmi."*  
> *(Installation blocked: Auto Blocker prevented the installation of apps from unauthorized sources)*

### Cara Mengatasinya:
1. Buka menu **Pengaturan (Settings)** pada ponsel Samsung Anda.
2. Gulir ke bawah dan pilih **Keamanan dan privasi (Security and privacy)**.
3. Temukan dan ketuk menu **Pemblokir Otomatis (Auto Blocker)**.
4. Ubah sakelar menjadi **Nonaktif (Turn OFF)** sementara waktu.
5. Buka kembali file `tatap-release-v<VERSION>.apk` melalui aplikasi **File Saya (My Files)** atau browser Anda, lalu lanjutkan proses instalasi seperti biasa.
6. *(Opsional)* Setelah Tatap berhasil terpasang, Anda dapat mengaktifkan kembali fitur *Auto Blocker* jika menginginkannya.

---

## 2. Peringatan Google Play Protect ("Aplikasi Tidak Dikenal" / "Diblokir")

Karena Tatap adalah proyek mandiri (*open-source*) yang didistribusikan langsung tanpa sertifikat pengembang komersial Google Play Store, sistem **Google Play Protect** terkadang menampilkan dialog peringatan:
> *"Aplikasi tidak dikenal"* atau *"Diblokir oleh Play Protect"*  
> *(Blocked by Play Protect: Unrecognized app developer)*

### Cara Mengatasinya:
1. Pada jendela pop-up peringatan Play Protect, jangan langsung menekan tombol *Batal* atau *OK*.
2. Ketuk teks **Rincian selengkapnya (More details)** dengan ikon panah kecil di bawah teks peringatan.
3. Ketuk opsi **Tetap instal (Install anyway)**.
4. Pemasangan akan dilanjutkan hingga selesai dan aplikasi dapat langsung dibuka.

---

## 3. Izin Memasang Aplikasi Tidak Dikenal (Install Unknown Apps)

Jika browser (Chrome, Samsung Internet) atau Pengelola Berkas (*File Manager*) Anda belum pernah digunakan untuk memasang APK:

### Cara Mengatasinya:
1. Saat membuka APK, sistem Android akan memunculkan dialog: *"Demi keamanan, ponsel Anda tidak diizinkan memasang aplikasi yang tidak dikenal dari sumber ini"*.
2. Ketuk tombol **Setelan (Settings)** pada dialog tersebut.
3. Aktifkan sakelar **Izinkan dari sumber ini (Allow from this source)**.
4. Tekan tombol *Kembali (Back)* satu kali, lalu ketuk **Instal (Install)**.

---

## 4. Pesan "Aplikasi Tidak Terpasang" (App Not Installed / Signature Conflict)

Jika muncul pesan singkat *"Aplikasi tidak terpasang"* atau *"Paket tampaknya tidak valid"*, penyebab paling umum adalah:

1. **Konflik Versi / Tanda Tangan:**  
   Ponsel Anda mungkin masih menyimpan instalan Tatap versi lama yang dibuat menggunakan tanda tangan *debug* atau sumber tidak resmi.
   - **Solusi:** Hapus instalan (*uninstall*) aplikasi Tatap yang saat ini ada di HP Anda, hidupkan ulang (*restart*) ponsel jika perlu, lalu pasang kembali berkas APK rilis resmi terbaru.
2. **Kekurangan Ruang Penyimpanan:**  
   Pastikan memori internal perangkat Anda masih memiliki ruang kosong minimal 200 MB untuk proses ekstraksi runtime Python lokal dan pustaka aplikasi.

---

## 5. Pesan "Ada Masalah Saat Mengurai Paket" (Parse Error)

Pesan ini muncul ketika sistem Android tidak dapat membaca berkas APK secara utuh:

1. **Berkas APK Terpotong / Korup:**  
   Unduhan lewat browser seluler terkadang terhenti sebelum selesai akibat fluktuasi sinyal internet.
   - **Solusi:** Periksa ukuran berkas APK pada manajer berkas. Berkas resmi Tatap Mobile memiliki ukuran sekitar **~35 MB s/d 36 MB**. Jika ukuran berkas yang terunduh hanya beberapa MB atau KB, silakan unduh ulang menggunakan koneksi Wi-Fi yang stabil.
2. **Salah Mengunduh Varian TV:**  
   Pastikan Anda mengunduh varian **Mobile** (`tatap-release-v<VERSION>.apk`), bukan varian Android TV (`tatap-tv-release-v<VERSION>.apk`).
3. **Versi Android Minimum:**  
   Tatap membutuhkan sistem operasi **Android 7.0 (Nougat, API level 24)** atau yang lebih baru.

---

## 6. Panduan Khusus Vendor Lainnya

### Xiaomi / Redmi / POCO (MIUI / HyperOS)
- Jika proses instalasi berhenti di tengah jalan, buka *Setelan > Setelan Tambahan > Opsi Pengembang*, lalu pastikan pengoptimalan sistem mengizinkan penginstalan paket via manajer berkas bawaan.
- Nonaktifkan sementara pemindaian antivirus bawaan saat memasang jika muncul peringatan false-positive.

### Infinix / Tecno / itel (XOS / HiOS)
- Saat membuka APK via *File Manager*, jika muncul aplikasi *Phone Master*, pilih opsi untuk melanjutkan pemasangan mandiri.

---

## 7. Masih Mengalami Kendala?

Jika Anda telah mengikuti seluruh panduan di atas namun masih tidak dapat memasang aplikasi:
1. Buka tiket laporan di [GitHub Issues Tatap](https://github.com/asfaraguest/tatap/issues).
2. Sertakan **tipe HP / model perangkat**, **versi Android & sistem antarmuka (misal: Galaxy A34 5G - One UI 6.1)**, serta **tangkapan layar (*screenshot*) pesan error yang muncul**. Tim pengembang akan dengan senang hati membantu menganalisis kendala Anda.
