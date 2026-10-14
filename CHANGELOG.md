# Changelog

Semua perubahan penting pada proyek **Tatap** didokumentasikan di berkas ini.

Format dokumen ini mengacu pada [Keep a Changelog](https://keepachangelog.com/id/1.1.0/), dan proyek ini sepenuhnya mematuhi [Semantic Versioning 2.0.0](https://semver.org/lang/id/).

---

## Prinsip Penomoran Versi (SemVer 2.0.0)

Format versi menggunakan skema `MAJOR.MINOR.PATCH`:
- **MAJOR (X.0.0):** Perubahan arsitektur mendasar atau modifikasi yang tidak kompatibel ke belakang (*breaking changes*).
- **MINOR (x.Y.0):** Penambahan fitur atau kapabilitas baru yang tetap kompatibel ke belakang (*backward-compatible new features*). Digit PATCH direset ke 0.
- **PATCH (x.y.Z):** Perbaikan bug, peningkatan stabilitas, atau perbaikan internal tanpa penambahan fitur baru (*backward-compatible bug fixes*).

## [2.7.0] - 2026-10-14

*Alasan kenaikan MINOR (2.6.0 → 2.7.0): penggabungan (merge) seluruh perubahan upstream v2.4.3 ke jalur fork personal — menghadirkan fitur dan peningkatan baru (perbaikan pemutaran 1080p, optimasi Android TV, UI) yang tetap kompatibel ke belakang. Fitur personal v2.5.0/v2.6.0 (favorit, filter katalog, branding Tatapan) tidak hilang.*

### Ditingkatkan
- **Sinkronisasi Upstream v2.4.3:** Merge `asfaraguest/tatap@63226a5` ke fork — termasuk: perbaikan stuttering pemutaran 1080p (async MediaCodec, buffer 25s/50s, HLS chunkless preparation, keepalive pool HTTPX 20/30), perbaikan zoom/crop awal pemutar, *true seamless quality switching* khusus Android TV, isolasi optimasi low-RAM Android TV (`largeHeap` TV, downsampling poster 180x260, buffer TV 8s/15s, PRAGMA SQLite hemat memori via `TATAP_IS_TV`, tuning GC), kompresi top-bar TV (10-foot UI), *floating navigation capsule* transparan, auto-dismiss banner proporsional panjang teks, dan optimasi performa low-end (panel solid tanpa blur, ambient blur 24px, RecyclerView tuning, animasi D-Pad 90ms).
- **Test Suite Diperluas:** `tests/test_regression_e2e.py` (E2E headless Chromium: player modal, subtitle dual-layer, navigasi episode, recovery koneksi) dan `tests/test_regression_playback.py` (rewrite m3u8 & audio demux proxy). Total suite: **26 test**.

### Diperbaiki
- **Portabilitas Test E2E (Chromium):** Path binary Chromium pada test E2E tidak lagi terikat satu mesin — dapat dioverride via env `TATAP_TEST_CHROME_PATH`, dengan fallback otomatis ke binary bawaan Playwright.

## [2.6.0] - 2026-10-14

*Alasan kenaikan MINOR (2.5.0 → 2.6.0): penambahan fitur filter katalog (sort Terbaru + filter tahun rilis) yang tetap kompatibel ke belakang.*

### Ditambahkan
- **Filter Katalog: Sort Terbaru & Filter Tahun (Android):** Tab Katalog kini memiliki panel filter: pilihan urutan **Populer** / **Terbaru** serta deretan chip **tahun rilis** (Semua, tahun berjalan s/d 1990, dapat di-scroll horizontal). Perintah terminal baru `:tahun <YYYY>` untuk menerapkan filter tahun langsung, lengkap dengan entri di dialog `:help`. Backend: `/api/browse` kini menerima juga nilai sort asli form filter hianime (`added_date`, `updated_date`, `release_date`, `title_az`, `avg_score`, `mal_score`, `most_viewed`, `most_followed`, `episode_count`).

### Diperbaiki
- **Pemetaan Nilai Sort Katalog:** Nilai sort lama yang tidak dikenali situs (`popularity`, `latest`, `score`, `az`, `most_favorite`) kini dipetakan ke nilai resmi (`""`, `added_date`, `avg_score`, `title_az`, `most_followed`) sehingga pilihan urutan benar-benar berfungsi alih-alih jatuh ke urutan default.

### Diubah
- **Nama Aplikasi Menjadi "Tatapan":** Label aplikasi diperbarui — mobile: **Tatapan** (sebelumnya "Tatap Personal"), TV: **Tatapan TV**. `applicationId` tetap `id.tatap.personal` / `id.tatap.personal.tv` agar jalur upgrade dari v2.5.0 tetap mulus tanpa instalasi ulang.

## [2.5.0] - 2026-10-14

*Alasan kenaikan MINOR (2.4.2 → 2.5.0): penambahan fitur favorit yang tetap kompatibel ke belakang. Perubahan `applicationId` hanya berlaku pada fork personal (`id.tatap.personal`) dan tidak mengubah perilaku versi resmi.*

### Ditambahkan
- **Fitur Star / Favorit Anime (Android + Backend):** Menambahkan sistem penanda favorit. Halaman detail kini memiliki tombol bintang (☆/★) untuk menandai atau menghapus anime dari daftar favorit; menu header beranda memiliki tombol **★ Favorit** yang membuka grid daftar favorit; terminal mendukung perintah `:favorit`. Sisi backend menambahkan tabel SQLite `favorites` serta endpoint `GET /api/favorites`, `GET /api/favorites/check`, `POST /api/favorites`, dan `DELETE /api/favorites`.

### Diubah
- **Rebranding Fork Personal (Tatap Personal):** `applicationId` Android diubah dari `id.tatap.app` menjadi `id.tatap.personal` (varian TV: `id.tatap.personal.tv`) dan nama aplikasi menjadi "Tatap Personal", sehingga dapat dipasang berdampingan dengan versi resmi tanpa saling menimpa.
- **Pemeriksa Pembaruan Mengarah ke Fork:** Endpoint `/api/update/check` kini memeriksa rilis terbaru dari repositori fork personal, bukan repositori upstream.
## [2.4.3] - 2026-10-14

### Ditingkatkan
- **True Seamless Quality Switching Khusus Android TV (Terisolasi Penuh):**
  - Meniadakan pemanggilan disruptif `player.stop()` dan `player.prepare()` saat pengguna mengganti resolusi video (misalnya dari 360p ke 1080p) pada Android TV (`TvFocusHelper.isTv()`).
  - Mengandalkan pembaruan dinamis `TrackSelectionParameters` pada Media3 ExoPlayer dan `app:surface_type="surface_view"`.
  - Video dan audio mengalir tanpa putus, tanpa jeda layar hitam, dan tanpa kemunculan spinner buffering saat pergantian kualitas berlangsung pada batas segmen/GOP berikutnya.
  - Varian Android Mobile tetap mempertahankan alur kode bawaannya secara terisolasi tanpa modifikasi.
- **Optimasi Kinerja dan Konsumsi Memori Khusus Android TV (Terisolasi Penuh):**
  - **Isolasi Bebas Efek Samping ke Android Mobile:** Seluruh penyesuaian parameter memori, connection pool, buffer pemutar, dan siklus render dibatasi secara ketat hanya untuk lingkungan Android TV (`TvFocusHelper.isTv()` dan `src/tv/AndroidManifest.xml`). Kode dan perilaku Android Mobile tetap berjalan 100% pada parameter bawaan tanpa modifikasi.
  - **Alokasi Heap Android TV:** Menambahkan `android:largeHeap="true"` khusus pada flavor Android TV (`src/tv/AndroidManifest.xml`) untuk memberikan headroom memori tambahan saat runtime CPython Chaquopy, cache database, dan ExoPlayer berjalan berdampingan pada perangkat TV dengan RAM terbatas (512MB–1GB).
  - **Downsampling Gambar Hemat Memori Khusus TV:** Memangkas target dekompresi poster anime pada Android TV dari 300x420 px menjadi 180x260 px di `ImageLoader.java` (menghemat ~63% memori per kartu poster pada layar TV 1080p). Menambahkan pemeriksaan pembatalan dini jika tampilan kartu telah didaur ulang (*view recycling*) sebelum proses decode bitmap dilakukan.
  - **Penyesuaian Cache View RecyclerView TV:** Menyetel `setItemViewCacheSize(4)` untuk navigasi remote D-Pad Android TV guna mencegah penumpukan hirarki tampilan di luar layar, sementara varian Mobile tetap mempertahankan 20 item untuk scrolling sentuh yang halus.
  - **Peniadaan Beban Komputasi Dynamic Shadow GPU:** Mengatur elevasi fokus kartu menjadi `0f` pada `TvFocusHelper.attachCardFocus` guna meniadakan kalkulasi bayangan drop shadow 3D pada GPU TV berdaya rendah (seperti Mali-450 / Mali-G31) saat tombol remote ditekan.
  - **Penyesuaian Buffer Video ExoPlayer TV:** Menyetel buffer video ExoPlayer pada Android TV menjadi 8 detik minimum dan 15 detik maksimum (dibandingkan 12s/25s pada Mobile), menghemat alokasi RAM playback tanpa memicu rebuffering pada koneksi stabil.
  - **Efisiensi Polling Subtitle:** Mengurangi frekuensi sinkronisasi subtitle pada TV dari interval 75ms menjadi 150ms serta membandingkan teks cue secara langsung dengan cache lokal tanpa alokasi string baru dari `getText().toString()`.
  - **Penjadwalan Pre-Resolve Episode Tetangga TV:** Menunda proses pre-resolve episode sebelum dan sesudah selama 20 detik setelah pemutaran video dimulai pada Android TV, mencegah persaingan CPU dan koneksi jaringan antara thread scraping dan hardware decoder video saat inisialisasi awal.
  - **Tuning Backend Python Rendah Memori:** Menyetel batas koneksi HTTPX pada backend menjadi `max_connections=8` dan `max_keepalive=3` saat berjalan di TV (`TATAP_IS_TV=1`), mengonfigurasi SQLite PRAGMA memori minimalis (`cache_size = -500`, `temp_store = FILE`, `mmap_size = 0`), menerapkan batas GC Python `(100, 5, 5)`, serta menghubungkan event Android `onTrimMemory` untuk memicu pembersihan sampah memori Python runtime secara berkala.
- **Kompresi Top-Bar Ergonomis Android TV (10-Foot UI):**
  - Memampatkan tinggi top-bar area pada Android TV: tinggi header dari 56dp menjadi 44dp, kolom pencarian dari 38dp menjadi 32dp, dan tombol tab segmentasi dari 34dp menjadi 30dp dengan padding vertikal yang ringkas (overscan vertikal disesuaikan dari 20dp ke 12dp).
  - Menghemat ~40dp ruang vertikal layar televisi tanpa mengurangi kenyamanan radius pandang 10 kaki (*10-foot viewing radius*) maupun keterbacaan teks font dan navigasi remote D-Pad.
  - Memperluas area tampilan grid anime di Android TV sehingga baris kartu kedua terlihat jelas tanpa perlu banyak scrolling dengan remote.
  - Memperkuat deteksi lingkungan TV di `TvFocusHelper.isTv()` dengan menyertakan deteksi package name Android TV (`.tv`) dan fitur sistem `android.software.leanback`.
- **Floating Navigation Capsule Transparan (Android UI):**
  - Mengubah panel navigasi bawah (`layout_pagination`) dari bilah footer solid statis 48dp menjadi kapsul melayang (*floating pill*) transparan setinggi 36dp dengan gaya *cyber glassmorphism* (`#CC090A12`, 80% opacity) dan aksen border cyan lembut (`#2B38BDF8`).
  - Menerapkan *edge-to-edge scrolling* pada `rv_anime_grid` dengan `paddingBottom="64dp"` dan `clipToPadding="false"`. Kartu anime mengalir mulus di bawah kapsul navigasi dan baris kartu terakhir tidak akan tertutup saat di-scroll ke paling bawah.
  - Mempertahankan interoperabilitas penuh Android TV D-Pad remote focus (`TvFocusHelper.attachFocusScale`) dengan visual border highlight cyan cerah saat tombol paginasi dipilih.
  - Menyembunyikan floating pill secara otomatis ketika grid berada dalam kondisi kosong (*empty state*) atau mengalami kegagalan koneksi awal agar tidak mengaburkan pesan error.
- **Auto-Dismiss Notification Timer Berbasis Panjang Teks (Android UI):**
  - Mengganti durasi statis 8 detik pada banner perintah/notifikasi (`showCommandOutput`) dengan kalkulasi timer baca dinamis yang proporsional dan ergonomis:
    - **Pesan Singkat (`<= 35 char`):** `2200ms` (2.2s) — ideal untuk pergantian tampilan/tab (`Tampilan diatur ke: MUSIM`, `:cari`, `:help`).
    - **Pesan Sedang (`36 - 65 char`):** `3200ms` (3.2s) — durasi pas untuk status eksekusi atau pergantian sumber stream.
    - **Pesan Panjang / Error:** `4500ms` (4.5s) — memberi waktu yang cukup bagi pengguna untuk membaca detail kesalahan koneksi atau instruksi perintah.
  - Menambahkan animasi transisi halus *fade-out* (alpha 220ms) saat notifikasi menghilang, menggantikan hilangnya banner secara mendadak (`GONE`).
  - Menambahkan dukungan *instant touch-to-dismiss*: mengetuk banner notifikasi secara langsung atau tombol silang penutup akan langsung menutup banner dengan transisi cepat.
- **Optimasi Performa Perangkat Spesifikasi Rendah (Web Desktop & Android):**
  - **Eliminasi Beban GPU Offscreen:** Mengganti penggunaan `backdrop-filter: blur(...)` pada drawer navigation menu dan gesture OSD player dengan permukaan solid gelap berpresisi tinggi (`--panel-solid`, `rgba(11, 13, 17, 0.96)`) dan border crisp. Mengurangi frame drop dan stuttering compositing GPU secara signifikan saat membuka drawer atau mengatur volume di laptop lawas dan Android TV.
  - **Optimasi Ambient Halo Video Player:** Mengurangi radius Gaussian blur `#ambient` dan `#ambient-fallback` dari 70px menjadi 24px (16px–20px pada resolusi mobile/tablet) dengan akselerasi layer hardware `transform: translate3d(0,0,0)` dan `will-change: transform, opacity`. Menghemat >70% GPU fillrate dan mempertahankan pemutaran video HLS pada 60 FPS stabil.
  - **CSS Layout Isolation:** Menambahkan `contain: content;` pada kartu poster (`.poster-card`) dan list item (`.trow`) sehingga perubahan hover atau mutasi DOM lokal tidak memicu re-layout satu halaman penuh.
  - **Atomic DOM Injection via DocumentFragment:** Membungkus seluruh perakitan elemen kartu hasil pencarian dan jadwal rilis di `term.js` ke dalam `DocumentFragment`, menggantikan mutasi DOM berulang per-item menjadi injeksi tunggal yang cepat.
  - **Asynchronous Image Decompression:** Menambahkan atribut `decoding="async"` dan `loading="lazy"` pada seluruh thumbnail dan poster anime di frontend web untuk mengalihkan dekompresi gambar keluar dari browser main thread.
  - **RecyclerView Cache & Low-End Tuning (Android):** Mengaktifkan `setHasFixedSize(true)`, `setItemViewCacheSize(20)`, dan drawing cache quality low pada `MainActivity.java` untuk pengalaman scroll instan tanpa re-measuring berulang.
  - **Animasi TV D-Pad Ringan (Android TV):** Menyetel durasi transisi fokus remote TV menjadi 90ms dan skala kartu 1.04x di `TvFocusHelper.java`, mengeliminasi lag shadow software pada chipset Android TV hemat daya.

### Diperbaiki
- **Eliminasi Stuttering & Patah-Patah Pemutaran Video 1080p (Android & Android TV):**
  - **Pencegahan Loop Rekonfigurasi Decoder di `onTracksChanged`:** Memasang guard boolean `hasAppliedTrackSelectionForStream` pada listener `onTracksChanged` agar seleksi track HLS hanya dieksekusi sekali saat manifest track pertama kali selesai di-resolve. Menghindari pemanggilan rekursif `setTrackSelectionParameters` yang memicu flush decoder dan micro-stuttering berulang kali saat pemutaran video sedang berlangsung.
  - **Ekspansi Buffer Video 1080p Aman (`min: 25s`, `max: 50s`):** Menyesuaikan buffer durasi `DefaultLoadControl` dari 8s/15s menjadi 25s minimum dan 50s maksimum dengan buffer mulai 2s dan rebuffer 4s serta menonaktifkan `prioritizeTimeOverSizeThresholds`. Menjamin buffer video 1080p tidak pernah mengalami starvation pada jaringan dinamis dengan alokasi RAM native yang tetap hemat (~10–15 MB).
  - **Aktivasi Asynchronous MediaCodec Buffer Queueing:** Mengonfigurasi `DefaultRenderersFactory.forceEnableMediaCodecAsynchronousQueueing()` pada `PlayerActivity.java` untuk memindahkan antrean input/output buffer decoding ke background looper thread, mencegah rendering loop terhambat pada chipset TV berbasis Android 9-11 (API 28-30).
  - **Aktivasi HLS Chunkless Preparation:** Mengaktifkan `setAllowChunklessPreparation(true)` pada `HlsMediaSource.Factory`, meniadakan pengunduhan segmen awal dari seluruh varian resolusi lain yang tidak diperlukan saat stream baru disiapkan.
  - **Eliminasi Teardown Codec di `onVideoSizeChanged`:** Menghapus pemanggilan disruptif `player.stop()` di tengah pemutaran video pada event perubahan ukuran surface, menjaga aliran decoding tetap mulus tanpa jeda restart.
  - **Pelepasan Batasan Minimum Resolusi Kaku:** Menghapus parameter `minW = 1600` dan `minH = 900` pada `applyHlsTrackSelection` serta menambahkan pengecekan `newParams.equals(current)` sebelum memicu update parameter track ke ExoPlayer.
  - **Restorasi HTTPX Keep-Alive Pool Backend:** Menyetel `max_keepalive_connections=20` dan `max_connections=30` dengan `keepalive_expiry=90.0` pada `_get_video_client`, meniadakan lonjakan CPU dari kalkulasi TLS 1.3 handshake berulang pada setiap pengunduhan segmen TS 1080p.
- **Perbaikan Inisialisasi Zoom/Crop Video Player (Android & Android TV):**
  - Mengatasi masalah di mana video HLS pada awal pemutaran selalu ter-zoom/terpotong (*cropped*) dan baru normal setelah pengguna berpindah resolusi ke 360p lalu ke 1080p lagi.
  - Mengonfigurasi `DefaultBandwidthMeter` dengan estimasi awal 25 Mbps (`25_000_000`) pada `ExoPlayer.Builder` agar ExoPlayer langsung memilih track video resolusi optimal (1080p/720p) sejak awal koneksi tanpa adaptasi lambat dari 360p yang mengunci surface buffer TV.
  - Memanggil `applyHlsTrackSelection(activeQuality)` secara eksplisit sebelum `player.prepare()`.
  - Memperbarui `applyHlsTrackSelection()` agar mendukung penuh kualitas `"best"`, `"hd"`, dan `"1080p"` dengan batasan resolusi yang presisi.
  - Mengaitkan `onTracksChanged(Tracks tracks)` di listener ExoPlayer dengan proteksi guard atomik untuk mengunci track override seketika setelah master manifest HLS selesai di-resolve tanpa loop rekursif.
  - Menetapkan atribut `app:surface_type="surface_view"` pada `PlayerView` di layout player untuk mengeliminasi pemotongan buffer dan tearing saat resolusi adaptif berubah tanpa memerlukan restart codec.
  - Menetapkan mode skala default `player.setVideoScalingMode(C.VIDEO_SCALING_MODE_SCALE_TO_FIT)` untuk memastikan video pas dengan layar tanpa pemotongan.
- **Anti-Ghosting & View Recycling Flicker (Android):** Memperbaiki bug tampilan pada daur ulang view RecyclerView di mana kartu yang di-scroll cepat sempat menampilkan poster anime sebelumnya secara keliru. Menyetel placeholder drawable solid netral (`#151822`) seketika sebelum thread decode background dijalankan pada `ImageLoader.java`.
- **Eliminasi Overdraw View Hierarchy (Android):** Menghapus background bertingkat yang redundan pada FrameLayout poster dan LinearLayout teks di dalam `item_anime_card.xml`, memotong beban pemindaian GPU fillrate hingga separuh pada perangkat mobile RAM 1GB–2GB.
- **2-Line Title Clamp & Tipografi Hybrid Minimalis:** Memperbaiki pemotongan judul anime romaji/Indo panjang pada kartu web dengan menerapkan 2-line clamp (`-webkit-line-clamp: 2` dan `min-height: 2.7em`), serta transisi ke sistem tipografi sans-serif modern yang proporsional untuk konten judul dan tetap mempertahankan monospace murni untuk terminal prompt, timestamp, dan statusbar.

## [2.4.2] - 2026-10-13

### Diperbaiki
- **Perbaikan Lifecycle Linux AppRun (Eliminasi Layar Putih & Font Unstyled):** Mengatasi bug kritis di mana peluncuran browser mode aplikasi (`google-chrome --app=...`) mendelegasikan proses ke instance browser yang sedang aktif sehingga proses CLI keluar seketika (< 100ms) dan memicu `trap cleanup EXIT` membunuh backend server FastAPI secara prematur. Menerapkan profil browser terisolasi (`--user-data-dir="${DATA_DIR}/browser-profile"`), fail-safe monitoring proses browser (jika browser mendelegasikan, tunggu dialihkan ke proses server agar backend tetap hidup), healthcheck mandiri via Python internal (bebas dependensi `curl`), dan pembersihan otomatis port 8767 stale sebelum startup.
- **Pencarian Multi-Sumber & Otomatis Fallback Otakudesu:** Memperbaiki subsistem pencarian di seluruh platform dengan meneruskan preferensi sumber aktif (`source`) dari frontend dan mengimplementasikan failover otomatis ke scraper Otakudesu apabila scraper HiAnime mengalami kendala jaringan atau Cloudflare challenge.
- **Perbaikan Input Terminal & Eliminasi Flash Putih:** Menghapus pencegahan ketik tombol slash (`/`) pada kolom pencarian terminal `#cmd` serta menambahkan inline background gelap `#08090c` pada tag `<html>` dan `<body>` di `index.html`.
- **Integrasi & Isolasi Tombol Filter Hari Rilis:** Memindahkan 3 tombol filter hari rilis (Kemarin, Hari Ini, Besok) ke dalam `.sec-head` sejajar dengan judul jadwal rilis menggunakan gaya segmented control (`.seg.schedule-days-bar`). Memproteksi visibilitasnya agar HANYA tampil saat view jadwal aktif (`terbaru`) dan otomatis disembunyikan di semua view lainnya (`cari`, `musim`, `lanjutan`, `katalog`, `recents`).
- **Penambahan Thumbnail Poster di List Pencarian & Jadwal Rilis:** Menambahkan thumbnail cover/poster mini (rasio 3:4) dengan *lazy-loading* dan fallback icon pada setiap item hasil pencarian (`view: cari`) dan jadwal rilis (`view: terbaru`), lengkap dengan metadata ringkas (tipe format, jumlah episode, status SUB/DUB) serta garis aksen visual jadwal hari ini (`.today`) dan besok (`.tomorrow`).
- **Perbaikan Overlap Bawah Desktop Web, Windows Portable & Linux AppImage:** Menghapus override cacat `--status-h: 36px` pada rentang resolusi desktop 901px–1280px yang sebelumnya menyebabkan kartu anime terbawah, tombol paginasi, dan jadwal rilis tertutup oleh `.bottom-bar`. Menetapkan baseline aman `--status-h: 88px`.
- **Navigasi Header Desktop & Scroll Safe Player Shell:** Menambahkan tombol drawer menu di bar header atas (`#btn-drawer-head`) untuk ergonomi pengguna desktop/laptop, menambahkan `overflow-y: auto` pada `.player-shell`, dan membatasi tinggi video windowed (`max-height: clamp(240px, 66vh, 640px)`) agar kontrol footer tidak terpotong pada laptop 768p.
- **Scrollbar Gelap Cyber Global:** Menerapkan styling scrollbar gelap kustom yang konsisten di seluruh WebKitGTK Linux AppImage, Edge WebView2 Windows Portable, dan Desktop Browser.

### Ditambahkan
- **Penyesuaian Skala Ukuran Font Subtitle Android TV:** Menambahkan 7 tingkatan ukuran font khusus perangkat Android TV (18sp, 22sp, 26sp [Standar TV], 30sp, 34sp [Jarak Jauh], 38sp [Layar Besar], dan 42sp [Maksimal]) untuk kenyamanan jarak pandang sofa 2.5m - 4m (10-foot UI).
- **Default Ukuran Font Adaptif TV:** Pengguna Android TV secara otomatis mendapatkan ukuran font standar 26sp (sebelumnya terbatas 17sp), sementara perangkat Mobile tetap menggunakan skala layar sentuh (14sp s/d 36sp, default 17sp).
- **Spasi Baris Dinamis & Line Spacing Multiplier:** Menerapkan `lineSpacingMultiplier="1.2"` pada layout XML dan `tvSubtitles.setLineSpacing(0f, 1.25f)` dinamis di Android TV agar kalimat subtitle panjang dua baris dengan font besar tidak saling bertumpuk bayangan (*shadow*).
- **Navigasi D-Pad Remote Dialog Ukuran Font:** Dialog pemilihan ukuran font mendukung navigasi remote kontrol D-pad secara penuh dengan auto-focus pada opsi aktif dan pengembalian fokus kontroler pemutar saat dialog ditutup.

### Ditingkatkan
- **Rebranding & Overhaul Mesin Penerjemah GTX+:** Memperbarui penamaan dan identitas mesin penerjemah AIGTX menjadi **GTX+ (Smart Fansub & Scene Detection)** di seluruh ekosistem (Backend FastAPI, Frontend Desktop Web/Windows/Linux, serta Android Mobile dan Android TV).
- **Integrasi Scene Detection Otomatis pada GTX+ Tanpa API Key:** Menerapkan deteksi konteks adegan (*scene detection*) adaptif langsung pada mesin GTX+ tanpa memerlukan API key pengguna. Adegan formal/kerajaan/militer dipertahankan baku dan santun, sedangkan adegan sehari-hari/sekolah/komedi otomatis diterjemahkan dengan gaya dialog lisan fansub santai (*casual conversation*).
- **Pengayaan Kamus Bahasa Fansub Casual Conversation:** Menambahkan puluhan leksikon dialog lisan santai fansub (*nggak, udah, cuma, banget, maksudmu apa, mana kutahu, beneran nih, pantesan, yang bener aja, jangan bercanda deh, sama sekali nggak, biar aku yang urus, gampang banget, cowok/cewek itu, mau gimana lagi*).
- **Kompatibilitas Mundur Penuh (Backward Compatibility):** Mendukung cache key `sub2|gtx+|` dengan pembacaan fallback `sub2|aigtx|`, parameter mode query `gtx+` dan `aigtx`, fungsi `_sanitize_aigtx_id = _sanitize_gtxplus_id`, serta prefix track URL `gtx+:<url>` dan `aigtx:<url>`.
- **Sinkronisasi Paritas Runtime Android:** Menyelaraskan seluruh modul penerjemah `backend/api/translate.py` dan `backend/main.py` ke `android/app/src/main/python/backend/` dengan 100% paritas kode.
- **Dokumentasi Pemetaan Teknis & Direktif AI Agent:** Menambahkan berkas master `PROJECT_MAP.md` yang memetakan topologi basis kode, data pipeline streaming/subtitle, skema database, indeks simbol fungsi utama, aturan paritas Chaquopy, serta menetapkan urutan baca wajib (`AGENTS.md` lalu `PROJECT_MAP.md`) sebelum perencanaan/iterasi bagi seluruh agen AI.

## [2.4.1] - 2026-10-13

### Diperbaiki
- **Pembersihan dan Pemulihan Engine Penerjemah Subtitle:** Mengatasi masalah fallback tidak diinginkan ke MyMemory yang menghasilkan terjemahan kaku. Menghapus penyimpanan cache MyMemory ke entri database `sub2|gtx`, memvalidasi dan membuang otomatis cache yang berisi pesan peringatan kuota MyMemory, serta memulihkan kualitas terjemahan luwes Google AIGTX dan AI Fansub.
- **Perbaikan Rute Endpoint Google Translate:** Menghapus parameter `client=gtx` yang diblokir/dibatasi laju (HTTP 429) oleh Google dan menggantinya dengan pool endpoint tanpa kuota berbasis `clients5.google.com` (`dict-chrome-ex` dan `tw-ob`) serta `translate.google.com` dengan konkurensi optimal 3 pekerja, memangkas durasi proses translasi satu episode penuh menjadi sangat cepat (< 5 detik).
- **Perbaikan Pemilihan Mode dan Model AI Fansub:** Memperbaiki identifikasi `job_key` inflight (`base_hash|lang|mode`) agar permintaan mode `ai` atau `aigtx` tidak dibajak oleh tugas prefetch `gtx`. Memperbarui model default Google AI Studio dari penamaan tidak valid `gemini-3.1-flash-lite` menjadi model aktif `gemini-2.0-flash` (dengan rantai failover `gemini-1.5-flash`), serta memperbaiki prioritas eksekusi mode AI agar langsung memanggil LLM fansub saat diminta.
- **Penanganan Aksi Refresh Subtitle di Pemutar:** Mengatasi bug pada dialog pemilih subtitle Android di mana eksekusi `[Refresh] Terjemahkan Ulang Subtitle` tertimpa oleh pemanggilan `applySubtitleSelection()` non-refresh.
- **Pencegahan Cache Poisoning Subtitle:** Memperbaiki bug kritis di mana kegagalan terjemahan sementara menyebabkan subtitle teks asli (bahasa Inggris) tersimpan ke database `subtitle_cache` lokal selama 7 hari, sehingga episode tersebut terkunci permanen dalam bahasa Inggris.
- **Validasi dan Pembersihan Cache Otomatis:** Sistem kini memvalidasi struktur kosakata bahasa Indonesia saat membaca cache subtitle. Entri cache lama yang terindikasi berisi teks mentah bahasa Inggris otomatis dihapus dan diterjemahkan ulang secara transparan.
- **Navigasi Next dan Previous Episode di ExoPlayer:** Mengatasi kendala tombol kontrol Next (`exo_next`) dan Previous (`exo_prev`) di `PlayerControlView` ExoPlayer (Media3) yang terkunci nonaktif secara internal akibat timeline MediaItem tunggal. Mengonfigurasi atribut layout XML `app:show_next_button="true"` dan `app:show_previous_button="true"`, memanggil `setShowNextButton(true)` dan `setShowPreviousButton(true)`, mengoreksi urutan inisialisasi agar `initExoPlayer` berjalan sebelum `setupExoNativeControls`, serta menerapkan logika batas navigasi optimistik sehingga tombol tetap responsif saat daftar episode sedang dimuat.
- **Pemuatan Metadata URL Episode dan Eliminasi Race Condition:** Memperbaiki penanganan respons endpoint resolver stream di mana master URL stream m3u8 tetap dipilih secara andal, membaca stream error secara tepat pada status non-200 tanpa melemparkan eksepsi prematur, mengisolasi setiap permintaan pemuatan stream dengan token identifikasi (`currentResolveLoadId`) agar pergantian episode beruntun tidak saling menimpa, serta menambahkan metadata judul serial dan nomor episode lengkap ke dalam `MediaMetadata` MediaItem Media3.
- **Pembersihan State saat Pergantian Episode:** Membersihkan referensi subtitle (`currentCues`, `currentSubLoadId`, teks overlay), stream URL, dan memanggil `player.clearMediaItems()` saat berpindah episode untuk mencegah tumpang tindih audio/video atau kebocoran subtitle episode sebelumnya.
- **Fallback Otakudesu pada Daftar Episode:** Memperbaiki endpoint `/api/anime/{slug}/episodes` agar secara otomatis beralih ke parser Otakudesu jika scraper HiAnime gagal atau anime berasal dari domain Otakudesu.

### Ditingkatkan
- **Kamus Idiom & Ungkapan Fansub Anime Universal:** Mengintegrasikan kamus referensi penerjemahan fansub anime yang komprehensif ke dalam mesin penerjemah `translate.py` (prompt sistem `_FANSUB_PROMPT_ID`, aturan normalisasi universal `_UNIVERSAL_FANSUB_RULES`, percakapan kasual `_CASUAL_FANSUB_RULES`, dan penghalus `_AIGTX_SMOOTH_RULES`). Mengeliminasi puluhan calque dan blunder penerjemahan mesin yang kaku (*"It can't be helped"* -> *"Mau gimana lagi"*, *"Give me a break"* -> *"Yang benar saja!"*, *"Serves you right"* -> *"Rasakan itu!"*, *"I'll take care of this"* -> *"Biar aku yang urus ini"*, *"Don't let your guard down"* -> *"Jangan lengah!"*, *"Stand back"* -> *"Mundur!"*, *"Over my dead body"* -> *"Langkahi dulu mayatku!"*, *"Piece of cake"* -> *"Gampang banget"*, *"Under the weather"* -> *"Kurang enak badan"*, *"Mendokusai"* -> *"Merepotkan sekali"*, *"Sasuga"* -> *"Sudah kuduga / Memang bisa diandalkan"*, serta ungkapan santai khas anime lainnya).
- **Sinkronisasi Penuh Aturan Translate Antar-Platform (Windows & Android):** Menyelaraskan seluruh modul dan berkas kamus penerjemah di `android/app/src/main/python/backend/` dengan repositori induk `backend/`. Memastikan runtime tersemat Chaquopy pada platform Android Mobile maupun Android TV memiliki 100% paritas aturan translasi, kamus kosakata atelier, dan penanganan fallback yang persis sama dengan platform Windows Portable dan Linux Desktop.
- **Kamus Referensi Fansub Fantasi & Atelier Sihir (Sampling Witch Hat Atelier):** Mengintegrasikan hasil audit dan sampling subtitle 13 episode *Witch Hat Atelier* ke dalam mesin penerjemah. Menambahkan kamus kosakata dunia sihir dan perapal mantra (*cast magic*, *conjuring ink*, *casting seal*, *magic stationer*, *witch apprentice*, *diadem herb*, *consent of the crown*) pada `_FANSUB_PROMPT_ID`, serta memperkaya filter penormalisasi `_UNIVERSAL_FANSUB_RULES`, `_CASUAL_FANSUB_RULES`, dan `_AIGTX_SMOOTH_RULES` guna mengeliminasi terjemahan kaku atau rancu (misal: "melakukan casting" menjadi "merapal sihir", "tinta sulap" menjadi "tinta sihir", "celah di tongkat" menjadi "retakan di tongkat", "toko alat tulis ajaib" menjadi "toko alat sihir", "memilih ramuan" menjadi "memetik herba", "sangat baik andal" menjadi "sangat mantap", "tiketnya terjual habis" menjadi "langsung ludes dalam sekejap", dan merapikan campuran kata ganti formal-santai). Perbaikan ini meningkatkan keluwesan tata bahasa untuk anime fantasi, atelier, petualangan, dan percakapan anime lainnya secara menyeluruh.
- **Menu Refresh / Terjemahkan Ulang Subtitle:** Menambahkan opsi aksi `[Refresh] Terjemahkan Ulang Subtitle (Hapus Cache)` pada dialog pemilih subtitle Android untuk membersihkan cache episode secara instan dan mengulang translasi dari awal.
- **Pacing dan Pembagian Mini-Batch Adaptif:** Mengurangi konkurensi pekerja menjadi 2 thread dengan jeda mikro antar batch dan mekanisme pembagian otomatis batch 20 baris menjadi 10 baris jika terjadi penolakan paket.
- **Pemuatan Asinkron Cadangan Daftar Episode di Pemutar:** Menambahkan `ensureEpisodeListLoaded()` di `PlayerActivity` untuk mengambil daftar episode secara otomatis jika pemutar dibuka langsung dari tautan riwayat atau intent eksternal tanpa membawa daftar episode lengkap.
- **Dukungan Tombol Fisik dan Keyboard Navigasi Episode:** Menambahkan pintasan `KEYCODE_N` (Next Episode) dan `KEYCODE_P` (Previous Episode) selain tombol media bawaan untuk kenyamanan pengendali remote TV dan keyboard fisik.

---

## [2.4.0] - 2026-10-12

### Ditambahkan
- **Fitur Jadwal Rilis 3 Hari:** Endpoint backend `/api/schedule` yang membatasi dan mengelompokkan jadwal tayang menjadi Kemarin, Hari Ini, dan Besok dengan zona waktu Indonesia Barat (WIB, UTC+7).
- **Filter Ketat Ketersediaan Judul:** Judul anime yang tidak tersedia pada scraper lokal otomatis dihapus dari jadwal sehingga setiap judul yang tampil dijamin dapat diputar.
- **Tab Jadwal Android Mobile:** Tab segmented `[Jadwal]` dan chip selector 3 hari khusus pada antarmuka Android Mobile (`!TvFocusHelper.isTv`).
- **Selector Chip Jadwal Web & Desktop:** Tombol filter interaktif 3 hari pada antarmuka Web, Windows Portable, dan Linux AppImage.
- **Fitur Navigasi Relasi Season Anime:** Endpoint `/api/anime/{slug}/relations` beserta tombol navigasi relasi (Prekuel, Season 1, Sekuel, Movie) di halaman detail anime.
- **Algoritma Origin Discovery:** Penelusuran rantai prekuel ke belakang (*backward-tracing*) untuk mendeteksi anime awal (Season 1) secara otomatis.
- **Counter Statistik Repositori di README:** Menambahkan badge counter real-time (GitHub Stars, Forks, Total Downloads, Repository Views/Hits, dan Open Issues) pada berkas `README.md`.

### Ditingkatkan
- **Optimasi Loading Episode Panjang:** Sistem caching dua lapis (SQLite backend dan memory cache) untuk serial dengan ratusan hingga ribuan episode, memangkas latensi pemuatan dari hitungan detik menjadi instan (< 50ms).
- **Format Jam Rilis pada Kartu:** Menampilkan label jam tayang WIB pada kartu anime di daftar jadwal.

### Diperbaiki
- **Isolasi Antarmuka Android TV:** Menjaga antarmuka Android TV tetap bersih dengan 3 tab standar tanpa merusak fokus navigasi D-pad.

---

## [2.3.16] - 2026-10-11

### Diperbaiki
- Reset sesi decoder saat perpindahan resolusi untuk mencegah distorsi zoom berlebih dan penyusutan layar (*shrink*) pada Android TV.

---

## [2.3.15] - 2026-10-11

### Diperbaiki
- Eliminasi masalah zoom dan pemulihan SurfaceView native dengan penskalaan rasio fit pada pemutar Android TV.

---

## [2.3.14] - 2026-10-11

### Diperbaiki
- Penghapusan loop resolusi melalui track override dan perbaikan penyusutan layar menggunakan TextureView fallback.

---

## [2.3.13] - 2026-10-11

### Diperbaiki
- Perbaikan garis hitam asimetris pada rasio aspek resolusi TV dan penambahan auto-focus pada hasil pencarian Android TV.

---

## [2.3.12] - 2026-10-11

### Diperbaiki
- Mengatasi java `EOFException` pada segmen video proxy HLS (`drama1.cfd`) dan peningkatan penanganan kegagalan socket.

---

## [2.3.11] - 2026-10-10

### Diperbaiki
- Eliminasi *double-probe* pada video proxy lokal, perpanjangan batas waktu koneksi (*connect timeout*), dan penambahan mekanisme stream retry.

---

## [2.3.10] - 2026-10-10

### Diperbaiki
- Mengatasi error sumber stream pada HLS anime yang sedang tayang (*ongoing*) dan penambahan fallback otomatis ke engine desync.

---

## [2.3.8] - 2026-10-10

### Diperbaiki
- Mengatasi masalah audio hening pada multi-rendition stream HiAnime saat beralih resolusi kualitas video.

---

## [2.3.7] - 2026-10-10

### Diperbaiki
- Perbaikan audio yang hilang pada stream puterin dan penyelarasan ukuran subtitle pada mode layar penuh.

---

## [2.3.6] - 2026-10-10

### Ditambahkan
- Desain ulang tata letak antarmuka Web, Windows, dan Linux dengan gaya modern bernuansa terminal.

---

## [2.3.4] - 2026-10-10

### Ditambahkan
- Integrasi pengaturan subtitle, pilihan kualitas video, dan rasio aspek langsung ke dalam kontroler bawaan ExoPlayer.

---

## [2.3.3] - 2026-10-10

### Ditambahkan
- Tombol navigasi episode berikutnya/sebelumnya (Next/Prev) pada kontroler native ExoPlayer serta mekanisme *background pre-resolving* stream episode lanjutan.

---

## [2.3.0] - 2026-10-10

### Ditambahkan
- **Inisiasi Arsitektur Android TV:** Penambahan target *product flavor* khusus TV (`tatap-tv-release-v*.apk`) terpisah dari Mobile.
- **Navigasi D-Pad TV:** Sistem penanganan fokus D-pad komprehensif (`TvFocusHelper`), penskalaan kartu (*card focus highlight*), dan dukungan remote televisi.
- **Standardisasi SemVer 2.0.0:** Penerapan aturan penomoran SemVer atomik di seluruh berkas proyek (`VERSION`, Android Gradle, dan script otomasi `tools/bump_version.py`).

---

## [2.2.0] - 2026-10-09

### Ditambahkan
- **Ekspansi Platform Android Mobile:** Peluncuran rilis perdana APK Android native menggunakan runtime Chaquopy Python lokal dan pemutar native ExoPlayer.
- **Rilis Multiplatform:** Standarisasi build rilis untuk Windows Portable, Linux AppImage, dan Android Mobile.

### Diperbaiki
- Penanganan rendering subtitle agar tetap aktif dan konsisten saat berpindah ke mode layar penuh.

---

## [2.1.0] - 2026-10-08

### Ditambahkan
- **Mesin Penerjemah AI Subtitle (BYOK):** Fitur auto-translate subtitle berbasis model bahasa besar (*Bring Your Own Key*) dengan dukungan Google Gemini, Groq Cloud, Ollama, dan OpenAI.
- Perintah terminal pemutar (`:gemini`, `:groq`, `:openai`, `:ollama`, `:model`, `:apikey`).

---

## [2.0.0] - 2026-10-05

### Diubah (Perombakan Arsitektur / Breaking Change)
- **Peluncur Native Desktop Standalone:** Beralih dari penggunaan tab browser peramban eksternal menjadi aplikasi native desktop mandiri (*standalone window*) berbasis Go launcher dan Microsoft Edge WebView2.
- **Integrasi Siklus Hidup Aplikasi:** Menutup jendela aplikasi secara otomatis mematikan backend lokal, dilengkapi proteksi instans tunggal (*single instance lock*).
- **Penyimpanan Terpusat:** Struktur penyimpanan lokal terisolasi di `webview2-data` dan database SQLite lokal.

---

## [1.1.0] - 2026-10-03

### Ditambahkan
- Dukungan multi-track subtitle dan pemilih dropdown subtitle di pemutar video.
- Migrasi skema database lokal untuk pencatatan preferensi subtitle pengguna.

---

## [1.0.0] - 2026-10-01

### Ditambahkan
- Inisiasi rilis perdana Tatap: Pemutar dan agregator anime mandiri tanpa server publik.
- Backend FastAPI lokal dengan scraping multi-sumber (HiAnime dan Otakudesu).
- Pemutar Web HLS dengan fitur Ambient Stage Light, penyesuaian rasio layar, dan proteksi bypass DPI via TLS desync.
