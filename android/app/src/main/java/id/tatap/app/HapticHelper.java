package id.tatap.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.os.Build;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.HapticFeedbackConstants;
import android.view.View;

/**
 * HapticHelper: Sentralisasi kendali umpan balik haptik (tactile feedback) untuk Android.
 * Menyediakan standardisasi getaran UI adaptif di seluruh aktivitas aplikasi,
 * dengan proteksi isolasi Android TV, adaptasi inersia motor koin ERM,
 * dan penyelarasan AudioAttributes.USAGE_MEDIA untuk Samsung One UI.
 */
public final class HapticHelper {
    private static volatile Vibrator cachedVibrator = null;

    private HapticHelper() {}

    /**
     * Memeriksa apakah getaran sentuh UI umum diaktifkan oleh pengguna.
     * Secara otomatis mengembalikan false pada perangkat Android TV.
     */
    public static boolean isHapticEnabled(Context context) {
        if (context == null || TvFocusHelper.isTv(context)) return false;
        try {
            SharedPreferences sp = context.getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
            return sp.getBoolean("pref_general_haptic", sp.getBoolean("pref_haptic", true));
        } catch (Throwable ignored) {
            return true;
        }
    }

    /**
     * Memeriksa apakah getaran adegan audio (Scene Haptic) diaktifkan oleh pengguna.
     * Default adalah false (tenang saat menonton).
     */
    public static boolean isSceneHapticEnabled(Context context) {
        if (context == null || TvFocusHelper.isTv(context)) return false;
        try {
            SharedPreferences sp = context.getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
            return sp.getBoolean("pref_scene_haptic", false);
        } catch (Throwable ignored) {
            return false;
        }
    }

    /**
     * Umpan balik mikro-tick halus (15ms / SEGMENT_TICK / CLOCK_TICK).
     * Digunakan untuk scrubbing timeline video, pergeseran volume/kecerahan,
     * perpindahan chip rentang episode, dan filter chip.
     */
    public static void performTick(View view) {
        if (view == null || !isHapticEnabled(view.getContext())) return;
        try {
            int feedbackConstant = Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE
                    ? HapticFeedbackConstants.SEGMENT_TICK
                    : (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                        ? HapticFeedbackConstants.CLOCK_TICK
                        : HapticFeedbackConstants.KEYBOARD_TAP);
            view.performHapticFeedback(
                    feedbackConstant,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
            );
        } catch (Throwable ignored) {}
        vibrateDirect(view.getContext(), 15, 70);
    }

    /**
     * Umpan balik klik standar (25ms / KEYBOARD_TAP).
     * Digunakan untuk penekanan tombol aksi, pergantian tab navigasi,
     * pemilihan kartu anime, play/pause, dan pemilihan episode.
     */
    public static void performClick(View view) {
        if (view == null || !isHapticEnabled(view.getContext())) return;
        try {
            view.performHapticFeedback(
                    HapticFeedbackConstants.KEYBOARD_TAP,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
            );
        } catch (Throwable ignored) {}
        vibrateDirect(view.getContext(), 25, 140);
    }

    /**
     * Umpan balik klik berbobot berat (45ms / DRAG_START / LONG_PRESS).
     * Digunakan untuk aksi bernilai tinggi seperti toggle Bookmark/Favorit,
     * Kunci Layar, dan switch aktivasi menu penting.
     */
    public static void performHeavyClick(View view) {
        if (view == null || !isHapticEnabled(view.getContext())) return;
        try {
            int feedbackConstant = Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE
                    ? HapticFeedbackConstants.DRAG_START
                    : HapticFeedbackConstants.LONG_PRESS;
            view.performHapticFeedback(
                    feedbackConstant,
                    HapticFeedbackConstants.FLAG_IGNORE_VIEW_SETTING | HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
            );
        } catch (Throwable ignored) {}
        vibrateDirect(view.getContext(), 45, 230);
    }

    /**
     * Mengalirkan getaran langsung via Vibrator hardware Android dengan:
     * 1. Kompensasi inersia mekanis motor koin ERM (durasi diskalakan bila tidak ada amplitude control).
     * 2. AudioAttributes.USAGE_MEDIA agar tidak dibungkam oleh Samsung One UI saat mode hemat daya/keyboard mute.
     */
    public static void vibrateDirect(Context context, long ms, int amplitude) {
        if (context == null || !isHapticEnabled(context)) return;
        try {
            Vibrator v = getVibrator(context);
            if (v == null || !v.hasVibrator()) return;

            long effectiveMs = ms;
            // Adaptasi motor ERM: motor koin butuh 35-50ms untuk mulai berputar
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !v.hasAmplitudeControl()) {
                if (effectiveMs <= 20) effectiveMs = 45;
                else if (effectiveMs <= 35) effectiveMs = 65;
                else if (effectiveMs <= 55) effectiveMs = 90;
            }

            AudioAttributes audioAttrs = null;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                audioAttrs = new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build();
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                int amp = (amplitude > 0) ? Math.max(1, Math.min(255, amplitude)) : -1;
                VibrationEffect effect = (amp > 0)
                        ? VibrationEffect.createOneShot(effectiveMs, amp)
                        : VibrationEffect.createOneShot(effectiveMs, VibrationEffect.DEFAULT_AMPLITUDE);
                if (audioAttrs != null) {
                    v.vibrate(effect, audioAttrs);
                } else {
                    v.vibrate(effect);
                }
            } else {
                v.vibrate(effectiveMs);
            }
        } catch (Throwable ignored) {}
    }

    private static Vibrator getVibrator(Context context) {
        if (cachedVibrator == null && context != null) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    android.os.VibratorManager vm = (android.os.VibratorManager) context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
                    if (vm != null) cachedVibrator = vm.getDefaultVibrator();
                }
                if (cachedVibrator == null) {
                    cachedVibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
                }
            } catch (Throwable ignored) {}
        }
        return cachedVibrator;
    }
}
