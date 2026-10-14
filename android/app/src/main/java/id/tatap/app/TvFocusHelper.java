package id.tatap.app;

import android.app.UiModeManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.view.View;
import android.widget.ImageButton;

import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;

public class TvFocusHelper {
    private static final int COLOR_FOCUSED_STROKE = Color.parseColor("#38BDF8");
    private static final int COLOR_NORMAL_STROKE = Color.parseColor("#1C202C");

    public static boolean isTv(Context context) {
        if (context == null) return false;
        if (context.getPackageName().endsWith(".tv")) {
            return true;
        }
        UiModeManager uiModeManager = (UiModeManager) context.getSystemService(Context.UI_MODE_SERVICE);
        if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {
            return true;
        }
        PackageManager pm = context.getPackageManager();
        if (pm.hasSystemFeature("android.software.leanback")) {
            return true;
        }
        // Fallback: perangkat tanpa layar sentuh adalah Android TV box / stick
        return !pm.hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN);
    }

    public static void attachFocusScale(final View view, final float targetScale, final float elevationDp) {
        if (view == null) return;
        view.setFocusable(true);
        view.setFocusableInTouchMode(false); // Di TV, remote fokus tidak membutuhkan touch mode

        final float density = view.getResources().getDisplayMetrics().density;
        final float elevationPx = elevationDp * density;

        view.setOnFocusChangeListener((v, hasFocus) -> {
            float scale = hasFocus ? targetScale : 1.0f;
            v.animate()
                    .scaleX(scale)
                    .scaleY(scale)
                    .setDuration(90)
                    .start();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                v.setElevation(hasFocus ? elevationPx : 0f);
                v.setTranslationZ(hasFocus ? elevationPx / 2f : 0f);
            }

            // Sorot border secara dinamis untuk CardView, MaterialButton, ImageButton, dan Custom Shaped Views
            if (v instanceof MaterialCardView) {
                MaterialCardView card = (MaterialCardView) v;
                card.setStrokeColor(hasFocus ? COLOR_FOCUSED_STROKE : COLOR_NORMAL_STROKE);
                card.setStrokeWidth(hasFocus ? (int) (2.5f * density) : (int) (1f * density));
            } else if (v instanceof MaterialButton) {
                MaterialButton btn = (MaterialButton) v;
                btn.setStrokeColor(ColorStateList.valueOf(hasFocus ? COLOR_FOCUSED_STROKE : Color.parseColor("#33FFFFFF")));
                btn.setStrokeWidth(hasFocus ? (int) (2.2f * density) : (int) (1f * density));
            } else if (v instanceof ImageButton) {
                ImageButton ib = (ImageButton) v;
                ib.setBackgroundColor(hasFocus ? Color.parseColor("#3338BDF8") : Color.TRANSPARENT);
            } else if (v.getBackground() instanceof GradientDrawable) {
                GradientDrawable gd = (GradientDrawable) v.getBackground().mutate();
                if (hasFocus) {
                    gd.setStroke((int) (2.2f * density), COLOR_FOCUSED_STROKE);
                } else {
                    gd.setStroke((int) (1f * density), Color.parseColor("#2B3448"));
                }
            }
        });
    }

    public static void attachCardFocus(final MaterialCardView card) {
        attachFocusScale(card, 1.04f, 0f);
    }
}
