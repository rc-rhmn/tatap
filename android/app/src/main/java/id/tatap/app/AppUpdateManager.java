package id.tatap.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import android.text.TextUtils;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.ImageButton;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import com.google.android.material.button.MaterialButton;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;

/**
 * Manajer In-App Update Tatap untuk Android (Mobile & Android TV / Google TV).
 * - Pemeriksaan pembaruan on-demand (manual only) via /api/update/check.
 * - Mengunduh berkas APK resmi bertanda tangan secara streaming dengan visual progress dialog.
 * - Mendukung navigasi D-Pad Android TV via TvFocusHelper.
 * - Meluncurkan PackageInstaller resmi OS Android via FileProvider.
 */
public class AppUpdateManager {

    public static final int REQUEST_CODE_INSTALL_PERMISSION = 7129;
    private static volatile AppUpdateManager instance;

    private volatile boolean isChecking = false;
    private volatile boolean isDownloading = false;
    private volatile boolean isDownloadCancelled = false;
    private Thread activeDownloadThread = null;
    private File pendingApkFile = null;

    public interface UpdateCheckListener {
        void onStatus(String message, boolean isError);
    }

    private AppUpdateManager() {}

    public static AppUpdateManager getInstance() {
        if (instance == null) {
            synchronized (AppUpdateManager.class) {
                if (instance == null) {
                    instance = new AppUpdateManager();
                }
            }
        }
        return instance;
    }

    /**
     * Memeriksa pembaruan secara manual.
     */
    public void checkUpdate(Activity activity) {
        checkUpdate(activity, null);
    }

    /**
     * Memeriksa pembaruan secara manual dengan listener status output konsol.
     */
    public void checkUpdate(Activity activity, UpdateCheckListener listener) {
        if (activity == null || activity.isFinishing()) return;

        if (isChecking) {
            Toast.makeText(activity, "Pemeriksaan pembaruan sedang berlangsung...", Toast.LENGTH_SHORT).show();
            return;
        }

        isChecking = true;
        if (listener != null) {
            listener.onStatus("> tatap$ Memeriksa pembaruan rilis Tatap...", false);
        }
        Toast.makeText(activity, "Memeriksa pembaruan rilis...", Toast.LENGTH_SHORT).show();

        new Thread(() -> {
            try {
                URL url = new URL("http://127.0.0.1:8767/api/update/check?force=true");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(10000);

                int code = conn.getResponseCode();
                if (code != 200) {
                    throw new IOException("Server lokal merespons HTTP " + code);
                }

                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
                reader.close();
                conn.disconnect();

                JSONObject res = new JSONObject(sb.toString());
                if (!res.optBoolean("success", false)) {
                    String msg = res.optString("error", "Gagal memeriksa pembaruan");
                    activity.runOnUiThread(() -> {
                        isChecking = false;
                        if (listener != null) listener.onStatus("> tatap$ Gagal memeriksa pembaruan: " + msg, true);
                        Toast.makeText(activity, msg, Toast.LENGTH_SHORT).show();
                    });
                    return;
                }

                JSONObject data = res.getJSONObject("data");
                boolean hasUpdate = data.optBoolean("has_update", false);
                String currentVer = data.optString("current_version", "2.9.2");
                String latestVer = data.optString("latest_version", currentVer);

                activity.runOnUiThread(() -> {
                    isChecking = false;
                    if (activity.isFinishing()) return;

                    if (hasUpdate) {
                        if (listener != null) {
                            listener.onStatus("> tatap$ Pembaruan rilis v" + latestVer + " tersedia!", false);
                        }
                        showUpdateDialog(activity, data);
                    } else {
                        if (listener != null) {
                            listener.onStatus("> tatap$ Tatap v" + currentVer + " adalah versi terbaru.", false);
                        }
                        Toast.makeText(activity, "✓ Tatap v" + currentVer + " sudah versi terbaru!", Toast.LENGTH_SHORT).show();
                    }
                });

            } catch (Exception e) {
                final String err = e.getMessage() != null ? e.getMessage() : "Koneksi gagal";
                activity.runOnUiThread(() -> {
                    isChecking = false;
                    if (activity.isFinishing()) return;
                    if (listener != null) {
                        listener.onStatus("> tatap$ Gagal memeriksa pembaruan: " + err, true);
                    }
                    Toast.makeText(activity, "Koneksi pembaruan gagal: " + err, Toast.LENGTH_SHORT).show();
                });
            }
        }).start();
    }

    /**
     * Menampilkan dialog modal pembaruan (vCurrent ➔ vLatest, release notes, tombol update).
     */
    public void showUpdateDialog(Activity activity, JSONObject data) {
        if (activity == null || activity.isFinishing()) return;

        Dialog dialog = new Dialog(activity);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        dialog.setContentView(R.layout.dialog_app_update);

        if (dialog.getWindow() != null) {
            dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
            int screenWidth = activity.getResources().getDisplayMetrics().widthPixels;
            int targetWidth = (int) (screenWidth * (TvFocusHelper.isTv(activity) ? 0.65f : 0.90f));
            dialog.getWindow().setLayout(targetWidth, ViewGroup.LayoutParams.WRAP_CONTENT);
        }

        TextView tvTitle = dialog.findViewById(R.id.tv_update_title);
        TextView tvBadge = dialog.findViewById(R.id.tv_update_version_badge);
        ImageButton btnClose = dialog.findViewById(R.id.btn_close_update_dialog);
        TextView tvNotes = dialog.findViewById(R.id.tv_update_notes);
        MaterialButton btnLater = dialog.findViewById(R.id.btn_update_later);
        MaterialButton btnNow = dialog.findViewById(R.id.btn_update_now);
        TextView tvFallback = dialog.findViewById(R.id.tv_update_fallback_browser);

        String currentVer = data.optString("current_version", "2.9.2");
        String latestVer = data.optString("latest_version", currentVer);
        String notes = data.optString("notes", data.optString("body", ""));
        String releaseUrl = data.optString("release_url", "https://github.com/asfaraguest/tatap/releases/latest");

        if (tvBadge != null) {
            tvBadge.setText("v" + currentVer + " ➔ v" + latestVer);
        }

        if (tvNotes != null) {
            if (TextUtils.isEmpty(notes)) {
                tvNotes.setText("Peningkatan performa, pemutakhiran katalog, dan perbaikan stabilitas.");
            } else {
                tvNotes.setText(notes.trim());
            }
        }

        JSONObject assets = data.optJSONObject("assets");
        String resolvedApkUrl = "";
        if (assets != null) {
            if (TvFocusHelper.isTv(activity)) {
                resolvedApkUrl = assets.optString("android_tv", "");
            }
            if (TextUtils.isEmpty(resolvedApkUrl)) {
                resolvedApkUrl = assets.optString("android", "");
            }
        }
        final String finalApkUrl = resolvedApkUrl;

        if (btnClose != null) {
            btnClose.setOnClickListener(v -> dialog.dismiss());
        }

        if (btnLater != null) {
            btnLater.setOnClickListener(v -> dialog.dismiss());
        }

        if (tvFallback != null) {
            tvFallback.setOnClickListener(v -> {
                try {
                    Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(releaseUrl));
                    activity.startActivity(browserIntent);
                } catch (Exception e) {
                    Toast.makeText(activity, "Gagal membuka browser: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                }
            });
        }

        if (btnNow != null) {
            btnNow.setOnClickListener(v -> {
                dialog.dismiss();
                if (TextUtils.isEmpty(finalApkUrl)) {
                    try {
                        Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(releaseUrl));
                        activity.startActivity(browserIntent);
                    } catch (Exception e) {
                        Toast.makeText(activity, "Gagal membuka browser: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                } else {
                    startDownload(activity, finalApkUrl, latestVer);
                }
            });
        }

        // Navigasi D-Pad untuk Android TV
        if (TvFocusHelper.isTv(activity)) {
            if (btnNow != null) TvFocusHelper.attachFocusScale(btnNow, 1.05f, 4f);
            if (btnLater != null) TvFocusHelper.attachFocusScale(btnLater, 1.05f, 4f);
            if (btnClose != null) TvFocusHelper.attachFocusScale(btnClose, 1.1f, 4f);
            if (tvFallback != null) TvFocusHelper.attachFocusScale(tvFallback, 1.05f, 2f);

            if (btnNow != null) {
                btnNow.requestFocus();
            }
        }

        dialog.show();
    }

    /**
     * Memulai pengunduhan APK streaming di background dengan dialog progress visual.
     */
    public void startDownload(Activity activity, String downloadUrl, String latestVer) {
        if (activity == null || activity.isFinishing()) return;

        if (isDownloading) {
            Toast.makeText(activity, "Pengunduhan pembaruan sedang berlangsung...", Toast.LENGTH_SHORT).show();
            return;
        }

        isDownloading = true;
        isDownloadCancelled = false;

        Dialog downloadDialog = new Dialog(activity);
        downloadDialog.requestWindowFeature(Window.FEATURE_NO_TITLE);
        downloadDialog.setContentView(R.layout.dialog_app_download);
        downloadDialog.setCancelable(false);

        if (downloadDialog.getWindow() != null) {
            downloadDialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
            int screenWidth = activity.getResources().getDisplayMetrics().widthPixels;
            int targetWidth = (int) (screenWidth * (TvFocusHelper.isTv(activity) ? 0.65f : 0.90f));
            downloadDialog.getWindow().setLayout(targetWidth, ViewGroup.LayoutParams.WRAP_CONTENT);
        }

        TextView tvTarget = downloadDialog.findViewById(R.id.tv_download_target_version);
        ProgressBar pbHorizontal = downloadDialog.findViewById(R.id.pb_download_horizontal);
        TextView tvStatus = downloadDialog.findViewById(R.id.tv_download_status);
        TextView tvPercent = downloadDialog.findViewById(R.id.tv_download_percent);
        MaterialButton btnCancel = downloadDialog.findViewById(R.id.btn_cancel_download);

        if (tvTarget != null) {
            tvTarget.setText("Versi Target: v" + latestVer);
        }
        if (pbHorizontal != null) {
            pbHorizontal.setMax(100);
            pbHorizontal.setProgress(0);
        }
        if (tvStatus != null) {
            tvStatus.setText("Menghubungkan ke server rilis...");
        }
        if (tvPercent != null) {
            tvPercent.setText("0%");
        }

        if (btnCancel != null) {
            btnCancel.setOnClickListener(v -> {
                isDownloadCancelled = true;
                if (activeDownloadThread != null) {
                    activeDownloadThread.interrupt();
                }
                try {
                    if (downloadDialog.isShowing()) downloadDialog.dismiss();
                } catch (Exception ignored) {}
            });

            if (TvFocusHelper.isTv(activity)) {
                TvFocusHelper.attachFocusScale(btnCancel, 1.05f, 4f);
                btnCancel.requestFocus();
            }
        }

        downloadDialog.show();

        activeDownloadThread = new Thread(() -> {
            File destDir = activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (destDir == null) destDir = activity.getExternalCacheDir();
            if (destDir == null) destDir = activity.getCacheDir();

            if (!destDir.exists()) {
                destDir.mkdirs();
            }

            String isTvSuffix = TvFocusHelper.isTv(activity) ? "-tv" : "";
            File targetApkFile = new File(destDir, "tatap" + isTvSuffix + "-release-v" + latestVer + ".apk");
            File tempApkFile = new File(destDir, "tatap" + isTvSuffix + "-release-v" + latestVer + ".apk.part");

            if (tempApkFile.exists()) tempApkFile.delete();
            if (targetApkFile.exists()) targetApkFile.delete();

            HttpURLConnection conn = null;
            InputStream in = null;
            FileOutputStream out = null;

            try {
                conn = openConnectionWithRedirects(downloadUrl);
                int responseCode = conn.getResponseCode();
                if (responseCode < 200 || responseCode >= 300) {
                    throw new IOException("Server rilis merespons HTTP " + responseCode);
                }

                long totalBytes = conn.getContentLengthLong();
                in = conn.getInputStream();
                out = new FileOutputStream(tempApkFile);

                byte[] buffer = new byte[8192];
                int len;
                long downloadedBytes = 0;
                long lastUiUpdate = 0;

                while ((len = in.read(buffer)) != -1) {
                    if (isDownloadCancelled) {
                        throw new InterruptedException("Unduhan dibatalkan oleh pengguna");
                    }
                    out.write(buffer, 0, len);
                    downloadedBytes += len;

                    long now = System.currentTimeMillis();
                    if (now - lastUiUpdate > 120 || downloadedBytes == totalBytes) {
                        lastUiUpdate = now;
                        final long cur = downloadedBytes;
                        final long tot = totalBytes;

                        activity.runOnUiThread(() -> {
                            if (downloadDialog.isShowing()) {
                                if (tot > 0) {
                                    int progress = (int) ((cur * 100) / tot);
                                    if (pbHorizontal != null) {
                                        pbHorizontal.setIndeterminate(false);
                                        pbHorizontal.setProgress(progress);
                                    }
                                    if (tvPercent != null) {
                                        tvPercent.setText(progress + "%");
                                    }
                                    double curMB = cur / (1024.0 * 1024.0);
                                    double totMB = tot / (1024.0 * 1024.0);
                                    if (tvStatus != null) {
                                        tvStatus.setText(String.format(Locale.US, "%.1f MB / %.1f MB", curMB, totMB));
                                    }
                                } else {
                                    double curMB = cur / (1024.0 * 1024.0);
                                    if (pbHorizontal != null) {
                                        pbHorizontal.setIndeterminate(true);
                                    }
                                    if (tvStatus != null) {
                                        tvStatus.setText(String.format(Locale.US, "%.1f MB terunduh", curMB));
                                    }
                                }
                            }
                        });
                    }
                }

                out.flush();
                out.close();
                out = null;
                in.close();
                in = null;

                if (targetApkFile.exists()) {
                    targetApkFile.delete();
                }
                boolean renamed = tempApkFile.renameTo(targetApkFile);
                File finalInstallApk = renamed ? targetApkFile : tempApkFile;

                activity.runOnUiThread(() -> {
                    isDownloading = false;
                    try {
                        if (downloadDialog.isShowing()) {
                            downloadDialog.dismiss();
                        }
                    } catch (Exception ignored) {}

                    Toast.makeText(activity, "Unduhan selesai! Memulai pemasangan...", Toast.LENGTH_SHORT).show();
                    installApk(activity, finalInstallApk);
                });

            } catch (InterruptedException ie) {
                if (tempApkFile.exists()) tempApkFile.delete();
                activity.runOnUiThread(() -> {
                    isDownloading = false;
                    try {
                        if (downloadDialog.isShowing()) downloadDialog.dismiss();
                    } catch (Exception ignored) {}
                    Toast.makeText(activity, "Pengunduhan pembaruan dibatalkan", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                if (tempApkFile.exists()) tempApkFile.delete();
                final String errMsg = e.getMessage() != null ? e.getMessage() : "Terjadi kesalahan jaringan";
                activity.runOnUiThread(() -> {
                    isDownloading = false;
                    try {
                        if (downloadDialog.isShowing()) downloadDialog.dismiss();
                    } catch (Exception ignored) {}
                    Toast.makeText(activity, "Gagal mengunduh: " + errMsg, Toast.LENGTH_LONG).show();
                });
            } finally {
                isDownloading = false;
                try { if (in != null) in.close(); } catch (Exception ignored) {}
                try { if (out != null) out.close(); } catch (Exception ignored) {}
                try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
            }
        });
        activeDownloadThread.start();
    }

    /**
     * Membuka koneksi HTTP dengan mengikuti redirect (301, 302, 303, 307, 308) ke storage hosting (GitHub -> S3).
     */
    private HttpURLConnection openConnectionWithRedirects(String urlStr) throws IOException {
        String currentUrl = urlStr;
        int redirects = 0;
        while (redirects < 10) {
            URL url = new URL(currentUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setInstanceFollowRedirects(true);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(30000);
            conn.setRequestProperty("User-Agent", "Tatap-Android (https://github.com/asfaraguest/tatap)");

            int status = conn.getResponseCode();
            if (status == HttpURLConnection.HTTP_MOVED_PERM ||
                status == HttpURLConnection.HTTP_MOVED_TEMP ||
                status == HttpURLConnection.HTTP_SEE_OTHER ||
                status == 307 || status == 308) {

                String newUrl = conn.getHeaderField("Location");
                if (newUrl != null && !newUrl.isEmpty()) {
                    if (newUrl.startsWith("/")) {
                        newUrl = url.getProtocol() + "://" + url.getHost() + newUrl;
                    }
                    conn.disconnect();
                    currentUrl = newUrl;
                    redirects++;
                    continue;
                }
            }
            return conn;
        }
        throw new IOException("Terlalu banyak pengalihan URL (" + redirects + ")");
    }

    /**
     * Meluncurkan PackageInstaller resmi Android via FileProvider.
     */
    public void installApk(Activity activity, File apkFile) {
        if (activity == null || activity.isFinishing() || apkFile == null || !apkFile.exists()) {
            return;
        }

        // Pengecekan izin REQUEST_INSTALL_PACKAGES pada Android 8.0+ (Oreo, API 26+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!activity.getPackageManager().canRequestPackageInstalls()) {
                this.pendingApkFile = apkFile;
                new AlertDialog.Builder(activity)
                        .setTitle("Izin Pemasangan Aplikasi")
                        .setMessage("Tatap memerlukan izin untuk memasang pembaruan langsung dari berkas APK resmi bertanda tangan. Silakan aktifkan 'Izinkan dari sumber ini' pada layar pengaturan.")
                        .setPositiveButton("Buka Pengaturan", (d, w) -> {
                            try {
                                Intent intent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES);
                                intent.setData(Uri.parse("package:" + activity.getPackageName()));
                                activity.startActivityForResult(intent, REQUEST_CODE_INSTALL_PERMISSION);
                            } catch (Exception e) {
                                try {
                                    Intent fallback = new Intent(Settings.ACTION_SECURITY_SETTINGS);
                                    activity.startActivity(fallback);
                                } catch (Exception ignored) {}
                            }
                        })
                        .setNegativeButton("Batal", null)
                        .show();
                return;
            }
        }

        try {
            Uri apkUri = FileProvider.getUriForFile(
                    activity,
                    activity.getPackageName() + ".fileprovider",
                    apkFile
            );

            Intent installIntent = new Intent(Intent.ACTION_VIEW);
            installIntent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            installIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            installIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity.startActivity(installIntent);
        } catch (Exception e) {
            Toast.makeText(activity, "Gagal meluncurkan penginstal paket: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    /**
     * Dipanggil dari Activity.onActivityResult saat kembali dari layar pengaturan izin install unknown apps.
     */
    public void onInstallPermissionResult(Activity activity) {
        if (activity == null || activity.isFinishing()) return;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (activity.getPackageManager().canRequestPackageInstalls()) {
                if (pendingApkFile != null && pendingApkFile.exists()) {
                    File toInstall = pendingApkFile;
                    pendingApkFile = null;
                    installApk(activity, toInstall);
                }
            } else {
                Toast.makeText(activity, "Izin pemasangan aplikasi tidak diberikan", Toast.LENGTH_SHORT).show();
            }
        }
    }
}
