package id.tatap.app;

import android.app.Activity;
import android.content.Context;
import android.media.AudioManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.GestureDetector;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.util.TypedValue;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageButton;

import androidx.media3.common.C;
import androidx.media3.common.Format;
import androidx.media3.common.ForwardingPlayer;
import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.datasource.DefaultHttpDataSource;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.exoplayer.DefaultLoadControl;
import androidx.media3.exoplayer.DefaultRenderersFactory;
import androidx.media3.exoplayer.upstream.DefaultBandwidthMeter;
import androidx.media3.exoplayer.hls.HlsMediaSource;
import androidx.media3.ui.AspectRatioFrameLayout;
import androidx.media3.ui.PlayerView;
import androidx.media3.ui.SubtitleView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PlayerActivity extends Activity {
    private ExoPlayer player;
    private ForwardingPlayer forwardingPlayer;
    private PlayerView playerView;
    private GestureDetector gestureDetector;
    private AudioManager audioManager;
    private View hudOsd;
    private TextView tvOsdIcon, tvOsdVal, tvRippleLeft, tvRippleRight;
    private ProgressBar pbOsdBar;
    private TextView tvPlayerTitle, tvSubStatus;
    private ImageButton btnPlayerBack;
    private View layoutTopBar;
    private View layoutBuffering;
    private TextView tvBufferingText;
    private TextView tvSubtitles;
    private final Handler handler = new Handler(Looper.getMainLooper());

    private String slug;
    private int ep;
    private String title;
    private List<Integer> episodeList = new ArrayList<>();
    private boolean isEpisodeListLoading = false;
    private View btnExoNext;
    private View btnExoPrev;
    private View btnExoSub;
    private View btnExoSettings;
    private View btnExoFullscreen;
    private Button btnAspect;
    private Button btnQuality;
    private Button btnSubStyle;
    private Button btnSubSelector;
    private float currentBrightness = 0.5f;
    private float currentVolumeFraction = -1f;

    // Subtitle Engine State
    public static class SubtitleCue {
        public final long startMs;
        public final long endMs;
        public final String text;

        public SubtitleCue(long startMs, long endMs, String text) {
            this.startMs = startMs;
            this.endMs = endMs;
            this.text = text;
        }
    }

    private volatile List<SubtitleCue> currentCues = new ArrayList<>();
    private int currentSubLoadId = 0;

    private String rawStreamUrl = "";
    private String streamReferer = "";
    private String masterStreamUrl = "";
    private int currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT;
    private final List<JSONObject> streamVariants = new ArrayList<>();
    private String activeQuality = "best";
    private List<JSONObject> subtitleTracks = new ArrayList<>();
    private String enSourceSubUrl = "";
    private String idNativeSubUrl = "";
    private String activeSubUrl = "";
    private String activeSubLang = "id"; // Default Indonesian
    private String activeEngine = "gtx"; // "gtx" | "gtx+" | "aigtx" | "ai" | "raw"
    private boolean subEnabled = true;
    private String activeStreamMode = "sub"; // "sub" | "dub"
    private boolean hasAiKey = false;
    private String configuredAiModel = "gemini-2.0-flash";
    private boolean isHlsMode = false;
    private boolean hasFallbackAttempted = false;
    private int currentResolveLoadId = 0;

    private boolean isHlsStream(String url) {
        if (url == null || url.isEmpty()) return false;
        String lower = url.toLowerCase();
        int qIdx = lower.indexOf('?');
        String path = (qIdx >= 0) ? lower.substring(0, qIdx) : lower;
        if (path.endsWith(".m3u8") || path.endsWith("/m3u8")) return true;
        if (path.endsWith(".ts") || path.endsWith(".ts.jpg") || path.endsWith(".jpg")
                || path.endsWith(".mp4") || path.endsWith(".m4s") || path.endsWith(".aac")) return false;
        return lower.contains(".m3u8")
                || lower.contains("format=m3u8")
                || lower.contains("output=m3u8")
                || lower.contains("/api/hls")
                || lower.contains("/hls/playlist");
    }

    private String lastSubtitleText = "";
    private boolean hasAppliedTrackSelectionForStream = false;
    private final Runnable subtitleSyncRunnable = new Runnable() {
        @Override
        public void run() {
            if (player != null && subEnabled) {
                long pos = player.getCurrentPosition();
                SubtitleCue active = findActiveCue(pos);
                if (active != null) {
                    if (tvSubtitles.getVisibility() != View.VISIBLE || !active.text.equals(lastSubtitleText)) {
                        lastSubtitleText = active.text;
                        tvSubtitles.setText(active.text);
                        tvSubtitles.setVisibility(View.VISIBLE);
                    }
                } else {
                    if (tvSubtitles.getVisibility() == View.VISIBLE) {
                        lastSubtitleText = "";
                        tvSubtitles.setText("");
                        tvSubtitles.setVisibility(View.GONE);
                    }
                }
            } else {
                if (tvSubtitles != null && tvSubtitles.getVisibility() == View.VISIBLE) {
                    lastSubtitleText = "";
                    tvSubtitles.setText("");
                    tvSubtitles.setVisibility(View.GONE);
                }
            }

            if (player != null && player.isPlaying()) {
                int syncInterval = TvFocusHelper.isTv(PlayerActivity.this) ? 150 : 75;
                handler.postDelayed(this, syncInterval);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                WindowManager.LayoutParams lp = getWindow().getAttributes();
                if (lp != null) {
                    lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
                    getWindow().setAttributes(lp);
                }
            }
        } catch (Throwable ignored) {}

        setContentView(R.layout.activity_player);

        // Pastikan hideSystemUi hanya dieksekusi setelah decorView terpasang di window
        try {
            getWindow().getDecorView().post(this::hideSystemUi);
        } catch (Throwable ignored) {}

        slug = getIntent().getStringExtra("slug");
        ep = getIntent().getIntExtra("ep", 1);
        title = getIntent().getStringExtra("title");
        ArrayList<Integer> passedList = getIntent().getIntegerArrayListExtra("episode_list");
        if (passedList != null) {
            episodeList.addAll(passedList);
        }
        ensureEpisodeListLoaded();

        playerView = findViewById(R.id.player_view);
        hudOsd = findViewById(R.id.hud_osd);
        tvOsdIcon = findViewById(R.id.tv_osd_icon);
        tvOsdVal = findViewById(R.id.tv_osd_val);
        pbOsdBar = findViewById(R.id.pb_osd_bar);
        tvRippleLeft = findViewById(R.id.tv_ripple_left);
        tvRippleRight = findViewById(R.id.tv_ripple_right);

        layoutTopBar = findViewById(R.id.layout_top_bar);
        tvPlayerTitle = findViewById(R.id.tv_player_title);
        tvSubStatus = findViewById(R.id.tv_sub_status);
        btnPlayerBack = findViewById(R.id.btn_player_back);

        layoutBuffering = findViewById(R.id.layout_buffering);
        tvBufferingText = findViewById(R.id.tv_buffering_text);
        tvSubtitles = findViewById(R.id.tv_subtitles);

        if (title != null && !title.isEmpty()) {
            tvPlayerTitle.setText(title + " - Ep " + ep);
        } else {
            tvPlayerTitle.setText("Episode " + ep);
        }

        if (btnPlayerBack != null) {
            btnPlayerBack.setOnClickListener(v -> finish());
        }

        btnAspect = findViewById(R.id.btn_aspect);
        if (btnAspect != null) {
            btnAspect.setOnClickListener(v -> cycleAspectRatio());
        }

        btnQuality = findViewById(R.id.btn_quality);
        if (btnQuality != null) {
            btnQuality.setOnClickListener(v -> showQualitySelectorDialog());
        }

        btnSubStyle = findViewById(R.id.btn_sub_style);
        if (btnSubStyle != null) {
            btnSubStyle.setOnClickListener(v -> showSubtitleStyleDialog());
        }

        btnSubSelector = findViewById(R.id.btn_sub_selector);
        if (btnSubSelector != null) {
            btnSubSelector.setOnClickListener(v -> showSubtitleSelectorDialog());
        }

        try {
            SharedPreferences sp = getSharedPreferences("tatap_player_prefs", MODE_PRIVATE);
            currentResizeMode = TvFocusHelper.isTv(this)
                    ? AspectRatioFrameLayout.RESIZE_MODE_FIT
                    : sp.getInt("aspect_mode", AspectRatioFrameLayout.RESIZE_MODE_FIT);
            activeEngine = sp.getString("pref_sub_engine", "gtx");
            if ("aigtx".equals(activeEngine)) activeEngine = "gtx+";
            activeSubLang = sp.getString("pref_sub_lang", "id");
            subEnabled = sp.getBoolean("pref_sub_enabled", true);
            if (playerView != null) {
                playerView.setResizeMode(currentResizeMode);
            }
            updateAspectButtonLabel();
        } catch (Throwable ignored) {}

        applySubtitleStyle();

        // Pasang respon fokus D-Pad TV pada tombol kontrol player
        TvFocusHelper.attachFocusScale(btnPlayerBack, 1.15f, 6f);
        TvFocusHelper.attachFocusScale(btnAspect, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnQuality, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnSubStyle, 1.08f, 6f);
        TvFocusHelper.attachFocusScale(btnSubSelector, 1.08f, 6f);

        try {
            audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        } catch (Throwable ignored) {}

        checkAiConfig();
        initExoPlayer();
        setupExoNativeControls();
        setupGestureControls();
        resolveAndPlayStream();
    }

    private void cycleAspectRatio() {
        try {
            if (playerView == null) return;
            if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FIT) {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_ZOOM;
                Toast.makeText(this, "Mode Layar: ZOOM (Penuh)", Toast.LENGTH_SHORT).show();
            } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FILL;
                Toast.makeText(this, "Mode Layar: FILL (Stretch)", Toast.LENGTH_SHORT).show();
            } else {
                currentResizeMode = AspectRatioFrameLayout.RESIZE_MODE_FIT;
                Toast.makeText(this, "Mode Layar: FIT (Skala Asli)", Toast.LENGTH_SHORT).show();
            }
            playerView.setResizeMode(currentResizeMode);
            getSharedPreferences("tatap_player_prefs", MODE_PRIVATE)
                    .edit().putInt("aspect_mode", currentResizeMode).apply();
            updateAspectButtonLabel();
        } catch (Throwable ignored) {}
    }

    private void updateAspectButtonLabel() {
        try {
            if (btnAspect == null) return;
            if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
                btnAspect.setText("Zoom");
            } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FILL) {
                btnAspect.setText("Fill");
            } else {
                btnAspect.setText("Fit");
            }
        } catch (Throwable ignored) {}
    }

    private void hideSystemUi() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                Window window = getWindow();
                if (window != null) {
                    android.view.WindowInsetsController controller = window.getInsetsController();
                    if (controller != null) {
                        controller.hide(android.view.WindowInsets.Type.statusBars() | android.view.WindowInsets.Type.navigationBars());
                        controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                    }
                }
            } else {
                View decorView = getWindow().getDecorView();
                if (decorView != null) {
                    decorView.setSystemUiVisibility(
                        View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                    );
                }
            }
        } catch (Throwable ignored) {}
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            try {
                hideSystemUi();
            } catch (Throwable ignored) {}
        }
    }

    private void checkAiConfig() {
        new Thread(() -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/settings").openConnection();
                conn.setConnectTimeout(2500);
                BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = r.readLine()) != null) sb.append(line);
                r.close();
                JSONObject res = new JSONObject(sb.toString());
                JSONObject d = res.optJSONObject("data");
                if (d == null) d = res;
                String k = d.optString("translate_apikey", "");
                String m = d.optString("translate_model", "gemini-2.0-flash");
                hasAiKey = !k.isEmpty();
                if (!m.isEmpty()) configuredAiModel = m;
            } catch (Exception ignored) {}
        }).start();
    }

    private void initExoPlayer() {
        DefaultLoadControl loadControl = new DefaultLoadControl.Builder()
                .setBufferDurationsMs(
                        25_000, // minBufferMs (25s - mencegah starvation di 1080p)
                        50_000, // maxBufferMs (50s)
                        2_000,  // bufferForPlaybackMs (2s cepat mulai)
                        4_000   // bufferForPlaybackAfterRebufferMs (4s)
                )
                .setPrioritizeTimeOverSizeThresholds(false)
                .build();

        // Bandwidth meter dengan estimasi awal tinggi (25 Mbps) agar ExoPlayer langsung
        // memilih track video beresolusi optimal (1080p/720p) saat pertama kali memutar,
        // mencegah hardware decoder Android TV terlanjur mengunci buffer di 360p yang menyebabkan video ter-crop/zoom.
        DefaultBandwidthMeter bandwidthMeter = new DefaultBandwidthMeter.Builder(this)
                .setInitialBitrateEstimate(25_000_000)
                .build();

        DefaultRenderersFactory renderersFactory = new DefaultRenderersFactory(this)
                .setExtensionRendererMode(DefaultRenderersFactory.EXTENSION_RENDERER_MODE_OFF)
                .setEnableDecoderFallback(true)
                .forceEnableMediaCodecAsynchronousQueueing();

        player = new ExoPlayer.Builder(this, renderersFactory)
                .setLoadControl(loadControl)
                .setBandwidthMeter(bandwidthMeter)
                .setSeekForwardIncrementMs(5000)
                .setSeekBackIncrementMs(5000)
                .build();

        player.setVideoScalingMode(C.VIDEO_SCALING_MODE_SCALE_TO_FIT);

        forwardingPlayer = new ForwardingPlayer(player) {
            @Override
            public boolean isCommandAvailable(int command) {
                if (command == COMMAND_SEEK_TO_NEXT_MEDIA_ITEM) {
                    return hasNextEpisode();
                }
                if (command == COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM) {
                    return hasPrevEpisode();
                }
                return super.isCommandAvailable(command);
            }

            @Override
            public Commands getAvailableCommands() {
                Commands.Builder builder = super.getAvailableCommands().buildUpon();
                if (hasNextEpisode()) {
                    builder.add(COMMAND_SEEK_TO_NEXT_MEDIA_ITEM);
                } else {
                    builder.remove(COMMAND_SEEK_TO_NEXT_MEDIA_ITEM);
                }
                if (hasPrevEpisode()) {
                    builder.add(COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM);
                } else {
                    builder.remove(COMMAND_SEEK_TO_PREVIOUS_MEDIA_ITEM);
                }
                return builder.build();
            }

            @Override
            public boolean hasNextMediaItem() {
                return hasNextEpisode();
            }

            @Override
            public boolean hasPreviousMediaItem() {
                return hasPrevEpisode();
            }

            @Override
            public void seekToNextMediaItem() {
                playNextEpisode();
            }

            @Override
            public void seekToPreviousMediaItem() {
                playPrevEpisode();
            }
        };
        playerView.setPlayer(forwardingPlayer);
        playerView.setShowNextButton(true);
        playerView.setShowPreviousButton(true);

        // Hide default ExoPlayer subtitle view since we use seamless custom overlay
        SubtitleView subView = playerView.getSubtitleView();
        if (subView != null) {
            subView.setVisibility(View.GONE);
        }

        player.addListener(new Player.Listener() {
            @Override
            public void onTracksChanged(androidx.media3.common.Tracks tracks) {
                // Saat manifest/tracks HLS baru selesai di-resolve pertama kali oleh ExoPlayer,
                // kunci track selection HANYA SEKALI agar target (1080p dsb.) terikat ke TrackGroup yang valid.
                // Proteksi boolean atomik mencegah loop rekursif pemanggilan setTrackSelectionParameters
                // yang menyebabkan decoder video terus-menerus di-flush saat pemutaran sedang berjalan.
                if (!hasAppliedTrackSelectionForStream && !tracks.isEmpty() && activeQuality != null && player != null) {
                    hasAppliedTrackSelectionForStream = true;
                    applyHlsTrackSelection(activeQuality);
                }
            }

            @Override
            public void onPlaybackStateChanged(int playbackState) {
                if (playbackState == Player.STATE_BUFFERING) {
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.VISIBLE);
                        if (tvBufferingText != null) tvBufferingText.setText("MEMUAT STREAM...");
                    }
                } else if (playbackState == Player.STATE_READY) {
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.GONE);
                    }
                } else if (playbackState == Player.STATE_ENDED) {
                    if (layoutBuffering != null) {
                        layoutBuffering.setVisibility(View.GONE);
                    }
                    if (hasNextEpisode()) {
                        Toast.makeText(PlayerActivity.this, "Episode selesai. Memutar Episode " + getNextEpisodeNumber() + "...", Toast.LENGTH_SHORT).show();
                        playNextEpisode();
                    }
                }
            }

            @Override
            public void onIsPlayingChanged(boolean isPlaying) {
                if (isPlaying) {
                    handler.removeCallbacks(subtitleSyncRunnable);
                    handler.post(subtitleSyncRunnable);
                }
            }

            @Override
            public void onPositionDiscontinuity(Player.PositionInfo oldPosition, Player.PositionInfo newPosition, int reason) {
                handler.post(subtitleSyncRunnable);
            }

            @Override
            public void onVideoSizeChanged(androidx.media3.common.VideoSize videoSize) {
                if (playerView != null) {
                    playerView.setResizeMode(currentResizeMode);
                    View sv = playerView.getVideoSurfaceView();
                    if (sv != null) {
                        sv.requestLayout();
                    }
                    playerView.requestLayout();
                }
            }

            @Override
            public void onPlayerError(PlaybackException error) {
                if (!hasFallbackAttempted && player != null && rawStreamUrl != null && !rawStreamUrl.isEmpty()) {
                    hasFallbackAttempted = true;
                    isHlsMode = !isHlsMode;
                    runOnUiThread(() -> applyCurrentStream());
                    return;
                }
                if (layoutBuffering != null) {
                    layoutBuffering.setVisibility(View.GONE);
                }
                String msg = error.getMessage();
                Throwable cause = error.getCause();
                if (cause != null && cause.getMessage() != null) {
                    msg += " (" + cause.getMessage() + ")";
                }
                Toast.makeText(PlayerActivity.this, "Player error: " + msg, Toast.LENGTH_LONG).show();
            }
        });

        playerView.setControllerVisibilityListener((PlayerView.ControllerVisibilityListener) visibility -> {
            boolean isVisible = (visibility == View.VISIBLE);
            if (layoutTopBar != null) {
                layoutTopBar.setVisibility(visibility);
            }
            if (isVisible) {
                handler.removeCallbacks(hideTopBarRunnable);
                handler.postDelayed(hideTopBarRunnable, 5000);
                bindExoControlButtons();
                updateExoButtonStates();
                if (btnExoSub != null) {
                    btnExoSub.setVisibility(View.VISIBLE);
                }
                if (btnExoSettings != null) {
                    btnExoSettings.setVisibility(View.VISIBLE);
                }
            } else {
                hideSystemUi();
            }
        });
    }

    private void setupGestureControls() {
        gestureDetector = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onSingleTapConfirmed(MotionEvent e) {
                // Toggle visibility top bar
                if (layoutTopBar.getVisibility() == View.VISIBLE) {
                    layoutTopBar.setVisibility(View.GONE);
                    hideSystemUi();
                } else {
                    layoutTopBar.setVisibility(View.VISIBLE);
                    handler.postDelayed(() -> {
                        if (player != null && player.isPlaying()) {
                            layoutTopBar.setVisibility(View.GONE);
                            hideSystemUi();
                        }
                    }, 4000);
                }
                return true;
            }

            @Override
            public boolean onDoubleTap(MotionEvent e) {
                float screenWidth = playerView.getWidth();
                float x = e.getX();

                if (x < screenWidth * 0.35f) {
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                } else if (x > screenWidth * 0.65f) {
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                } else {
                    if (player.isPlaying()) {
                        player.pause();
                    } else {
                        player.play();
                    }
                }
                vibrate(25);
                return true;
            }

            @Override
            public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX, float distanceY) {
                if (e1 == null || e2 == null) return false;
                float deltaY = e1.getY() - e2.getY();
                float screenWidth = playerView.getWidth();

                if (Math.abs(distanceY) > Math.abs(distanceX)) {
                    if (e1.getX() < screenWidth * 0.5f) {
                        adjustBrightness(distanceY / playerView.getHeight());
                    } else {
                        adjustVolume(distanceY / playerView.getHeight());
                    }
                    return true;
                }
                return false;
            }
        });

        playerView.setOnTouchListener((v, event) -> {
            if (event.getAction() == MotionEvent.ACTION_DOWN) {
                if (audioManager != null) {
                    int maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
                    int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
                    currentVolumeFraction = maxVol > 0 ? ((float) curVol / (float) maxVol) : 0f;
                }
            } else if (event.getAction() == MotionEvent.ACTION_UP || event.getAction() == MotionEvent.ACTION_CANCEL) {
                currentVolumeFraction = -1f;
            }
            gestureDetector.onTouchEvent(event);
            return false;
        });
    }

    private final Runnable hideTopBarRunnable = this::hideTopBar;

    private void showTopBarBriefly() {
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(View.VISIBLE);
            handler.removeCallbacks(hideTopBarRunnable);
            handler.postDelayed(hideTopBarRunnable, 5000);
        }
    }

    private void hideTopBar() {
        if (layoutTopBar != null) {
            layoutTopBar.setVisibility(View.GONE);
            if (playerView != null) {
                playerView.requestFocus();
            }
            hideSystemUi();
        }
    }

    private boolean isViewOrChildFocused(View parent) {
        if (parent == null || parent.getVisibility() != View.VISIBLE) return false;
        if (parent.isFocused()) return true;
        if (parent instanceof ViewGroup) {
            View current = getCurrentFocus();
            if (current != null) {
                View p = current;
                while (p != null) {
                    if (p == parent) return true;
                    if (p.getParent() instanceof View) {
                        p = (View) p.getParent();
                    } else {
                        break;
                    }
                }
            }
        }
        return false;
    }

    private boolean isChildOf(View child, View parent) {
        if (child == null || parent == null) return false;
        if (child == parent) return true;
        View p = child;
        while (p != null) {
            if (p == parent) return true;
            if (p.getParent() instanceof View) {
                p = (View) p.getParent();
            } else {
                break;
            }
        }
        return false;
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            int keyCode = event.getKeyCode();
            boolean isTopBarActive = (layoutTopBar != null && layoutTopBar.getVisibility() == View.VISIBLE);
            boolean hasFocusOnTopBar = isTopBarActive && isViewOrChildFocused(layoutTopBar);

            switch (keyCode) {
                case KeyEvent.KEYCODE_MENU:
                case KeyEvent.KEYCODE_SETTINGS:
                case KeyEvent.KEYCODE_INFO:
                    showPlayerUnifiedSettingsDialog();
                    return true;

                case KeyEvent.KEYCODE_DPAD_CENTER:
                case KeyEvent.KEYCODE_ENTER:
                    if (hasFocusOnTopBar) {
                        View focused = getCurrentFocus();
                        if (focused != null && isChildOf(focused, layoutTopBar)) {
                            showTopBarBriefly();
                            focused.performClick();
                            return true;
                        }
                    }
                    if (player != null) {
                        if (player.isPlaying()) {
                            player.pause();
                            showTopBarBriefly();
                        } else {
                            player.play();
                            hideTopBar();
                        }
                        vibrate(20);
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                    if (player != null) {
                        if (player.isPlaying()) {
                            player.pause();
                            showTopBarBriefly();
                        } else {
                            player.play();
                            hideTopBar();
                        }
                        vibrate(20);
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PLAY:
                    if (player != null && !player.isPlaying()) {
                        player.play();
                        hideTopBar();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PAUSE:
                    if (player != null && player.isPlaying()) {
                        player.pause();
                        showTopBarBriefly();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_NEXT:
                case KeyEvent.KEYCODE_PAGE_DOWN:
                case KeyEvent.KEYCODE_N:
                    if (hasNextEpisode()) {
                        playNextEpisode();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                case KeyEvent.KEYCODE_PAGE_UP:
                case KeyEvent.KEYCODE_P:
                    if (hasPrevEpisode()) {
                        playPrevEpisode();
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_DPAD_LEFT:
                    if (hasFocusOnTopBar) {
                        showTopBarBriefly();
                        break; // Jangan seek, biarkan navigasi fokus antar tombol
                    }
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_MEDIA_REWIND:
                    seekRelative(-5000);
                    showRipple(tvRippleLeft);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_DPAD_RIGHT:
                    if (hasFocusOnTopBar) {
                        showTopBarBriefly();
                        break; // Jangan seek, biarkan navigasi fokus antar tombol
                    }
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_MEDIA_FAST_FORWARD:
                    seekRelative(5000);
                    showRipple(tvRippleRight);
                    vibrate(15);
                    return true;

                case KeyEvent.KEYCODE_DPAD_UP:
                    showTopBarBriefly();
                    if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                        btnSubSelector.requestFocus();
                        return true;
                    }
                    if (playerView != null) {
                        playerView.showController();
                    }
                    break;

                case KeyEvent.KEYCODE_DPAD_DOWN:
                    if (isTopBarActive) {
                        hideTopBar();
                        return true;
                    }
                    if (playerView != null) {
                        if (playerView.isControllerFullyVisible()) {
                            playerView.hideController();
                        } else {
                            playerView.showController();
                        }
                        return true;
                    }
                    break;

                case KeyEvent.KEYCODE_BACK:
                    if (isTopBarActive) {
                        hideTopBar();
                        return true;
                    }
                    break;
            }
        }
        return super.dispatchKeyEvent(event);
    }

    private void seekRelative(long deltaMs) {
        if (player != null) {
            long newPos = Math.max(0, Math.min(player.getDuration(), player.getCurrentPosition() + deltaMs));
            player.seekTo(newPos);
            handler.post(subtitleSyncRunnable);
        }
    }

    private void adjustVolume(float percent) {
        if (audioManager == null) return;
        int maxVol = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        if (maxVol <= 0) return;

        if (currentVolumeFraction < 0) {
            int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
            currentVolumeFraction = (float) curVol / (float) maxVol;
        }

        // Akumulator float kontinu (sama seperti brightness) agar gerakan lambat tidak terpotong menjadi 0
        currentVolumeFraction = Math.max(0.0f, Math.min(1.0f, currentVolumeFraction + (percent * 1.2f)));
        int targetVol = Math.round(currentVolumeFraction * maxVol);
        int curVol = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC);
        if (targetVol != curVol) {
            audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, targetVol, 0);
        }

        int pct = Math.round(currentVolumeFraction * 100);
        showOsd(targetVol == 0 ? "MUTE" : "VOL", pct);
    }

    private void adjustBrightness(float percent) {
        currentBrightness = Math.max(0.05f, Math.min(1.0f, currentBrightness + (percent * 1.2f)));
        WindowManager.LayoutParams lp = getWindow().getAttributes();
        lp.screenBrightness = currentBrightness;
        getWindow().setAttributes(lp);

        int pct = (int) (currentBrightness * 100);
        showOsd("BRT", pct);
    }

    private void showOsd(String icon, int pct) {
        tvOsdIcon.setText(icon);
        pbOsdBar.setProgress(pct);
        tvOsdVal.setText(pct + "%");
        hudOsd.setVisibility(View.VISIBLE);
        handler.removeCallbacks(hideOsdRunnable);
        handler.postDelayed(hideOsdRunnable, 1200);
    }

    private final Runnable hideOsdRunnable = () -> hudOsd.setVisibility(View.GONE);

    private void showRipple(TextView tv) {
        tv.setVisibility(View.VISIBLE);
        handler.postDelayed(() -> tv.setVisibility(View.GONE), 350);
    }

    private void vibrate(long ms) {
        Vibrator v = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        if (v != null && v.hasVibrator()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
            } else {
                v.vibrate(ms);
            }
        }
    }

    private void resolveAndPlayStream() {
        resolveAndPlayStream(currentResolveLoadId);
    }

    private void resolveAndPlayStream(final int resolveId) {
        runOnUiThread(() -> {
            if (layoutBuffering != null) {
                layoutBuffering.setVisibility(View.VISIBLE);
                if (tvBufferingText != null) tvBufferingText.setText("MENYIAPKAN STREAM...");
            }
        });

        new Thread(() -> {
            try {
                if (resolveId != currentResolveLoadId) return;

                SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
                activeQuality = sp.getString("pref_quality", "best");

                String u = "http://127.0.0.1:8767/api/stream/resolve?slug=" + URLEncoder.encode(slug != null ? slug : "", "UTF-8")
                        + "&ep=" + ep + "&mode=sub&q=" + URLEncoder.encode(activeQuality != null ? activeQuality : "best", "UTF-8");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(20000);
                int code = conn.getResponseCode();
                InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
                if (is == null) {
                    throw new IOException("HTTP " + code + " tanpa respons");
                }
                BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();
                conn.disconnect();

                if (resolveId != currentResolveLoadId) return;

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONObject data = res.getJSONObject("data");
                    activeStreamMode = data.optString("mode", "sub");
                    String streamUrl = "";
                    String masterUrl = data.optString("master", "");
                    if (!masterUrl.isEmpty()) {
                        streamUrl = masterUrl;
                    } else if (data.has("picked")) {
                        streamUrl = data.getJSONObject("picked").optString("url");
                    } else if (data.has("variants")) {
                        JSONArray vars = data.getJSONArray("variants");
                        if (vars.length() > 0) {
                            streamUrl = vars.getJSONObject(0).optString("url");
                        }
                    }
                    String referer = data.optString("referer", "");

                    // Simpan stream variants untuk selector resolusi
                    JSONArray varsArr = data.optJSONArray("variants");
                    streamVariants.clear();
                    if (varsArr != null) {
                        for (int i = 0; i < varsArr.length(); i++) {
                            streamVariants.add(varsArr.getJSONObject(i));
                        }
                    }
                    String pickedQ = "HD";
                    if (data.has("picked")) {
                        pickedQ = data.getJSONObject("picked").optString("q", "HD");
                    } else if (!streamVariants.isEmpty()) {
                        pickedQ = streamVariants.get(0).optString("q", "HD");
                    }
                    activeQuality = pickedQ;

                    isHlsMode = isHlsStream(masterUrl) || isHlsStream(streamUrl)
                            || (!streamVariants.isEmpty() && isHlsStream(streamVariants.get(0).optString("url", "")));
                    hasFallbackAttempted = false;

                    // Simpan subtitle tracks yang tersedia
                    JSONArray subArr = data.optJSONArray("subtitles");
                    subtitleTracks.clear();
                    String foundEnSub = "";
                    String foundIdSub = "";
                    String foundDefSub = "";
                    String foundNonArSub = "";

                    if (subArr != null) {
                        for (int i = 0; i < subArr.length(); i++) {
                            JSONObject s = subArr.getJSONObject(i);
                            subtitleTracks.add(s);
                            String lang = s.optString("lang", "").toLowerCase();
                            String lbl = s.optString("label", "").toLowerCase();
                            String url = s.optString("url", "");
                            boolean isDef = s.optBoolean("default", false);

                            boolean isArabic = lang.equals("ar") || lang.equals("ara") || lbl.contains("arabic") || lbl.contains("arab");
                            boolean isEnglish = lang.equals("en") || lang.equals("eng") || lbl.contains("english") || lbl.startsWith("eng");
                            boolean isIndo = lang.equals("id") || lang.equals("ind") || lbl.contains("indonesia") || lbl.contains("bahasa");

                            if (foundEnSub.isEmpty() && isEnglish && !url.isEmpty()) {
                                foundEnSub = url;
                            }
                            if (foundIdSub.isEmpty() && isIndo && !url.isEmpty()) {
                                foundIdSub = url;
                            }
                            if (foundDefSub.isEmpty() && isDef && !isArabic && !url.isEmpty()) {
                                foundDefSub = url;
                            }
                            if (foundNonArSub.isEmpty() && !isArabic && !url.isEmpty()) {
                                foundNonArSub = url;
                            }
                        }
                    }

                    // Backend juga menyediakan resolved default sub di data.optString("sub")
                    String backendSub = data.optString("sub", "");
                    String backendSubLang = data.optString("sub_lang", "").toLowerCase();
                    boolean backendIsArabic = backendSubLang.contains("arab") || backendSubLang.equals("ar");

                    if (foundEnSub.isEmpty()) {
                        if (!backendSub.isEmpty() && !backendIsArabic) {
                            foundEnSub = backendSub;
                        } else if (!foundDefSub.isEmpty()) {
                            foundEnSub = foundDefSub;
                        } else if (!foundNonArSub.isEmpty()) {
                            foundEnSub = foundNonArSub;
                        } else if (!subtitleTracks.isEmpty()) {
                            foundEnSub = subtitleTracks.get(0).optString("url", "");
                        }
                    }

                    enSourceSubUrl = foundEnSub;
                    idNativeSubUrl = foundIdSub;

                    // Tentukan activeSubUrl berdasarkan preferensi engine saat ini
                    if ("id".equals(activeSubLang) && "raw".equals(activeEngine) && !idNativeSubUrl.isEmpty()) {
                        activeSubUrl = idNativeSubUrl;
                    } else if ("en".equals(activeSubLang) && "raw".equals(activeEngine)) {
                        activeSubUrl = enSourceSubUrl;
                    } else {
                        // Terjemahan (AIGTX, AI, GTX) menggunakan enSourceSubUrl sebagai sumber terjemahan
                        activeSubUrl = !enSourceSubUrl.isEmpty() ? enSourceSubUrl : (foundNonArSub.isEmpty() ? foundEnSub : foundNonArSub);
                    }

                    rawStreamUrl = streamUrl;
                    streamReferer = referer;
                    masterStreamUrl = (!masterUrl.isEmpty() && isHlsStream(masterUrl)) ? masterUrl : "";

                    if (!rawStreamUrl.isEmpty()) {
                        runOnUiThread(() -> {
                            if (resolveId != currentResolveLoadId) return;
                            if (btnQuality != null && activeQuality != null) {
                                btnQuality.setText(activeQuality.toUpperCase());
                            }
                            applyCurrentStream();
                            preResolveNeighbors();
                        });
                    } else {
                        runOnUiThread(() -> {
                            if (resolveId != currentResolveLoadId) return;
                            if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                            Toast.makeText(this, "URL stream video tidak ditemukan untuk episode ini", Toast.LENGTH_LONG).show();
                        });
                    }
                } else {
                    runOnUiThread(() -> {
                        if (resolveId != currentResolveLoadId) return;
                        if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                        Toast.makeText(this, "Gagal resolve: " + res.optString("error"), Toast.LENGTH_LONG).show();
                    });
                }
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (resolveId != currentResolveLoadId) return;
                    if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
                    Toast.makeText(this, "Error streaming: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                });
            }
        }).start();
    }

    private void applyCurrentStream() {
        if (rawStreamUrl.isEmpty()) return;

        if (layoutBuffering != null) {
            layoutBuffering.setVisibility(View.VISIBLE);
            if (tvBufferingText != null) tvBufferingText.setText("MEMUAT STREAM...");
        }

        try {
            boolean isHls = isHlsMode || isHlsStream(rawStreamUrl) || isHlsStream(streamReferer);

            String proxiedVideo = "http://127.0.0.1:8767/api/player/video?url=" + Uri.encode(rawStreamUrl)
                    + "&referer=" + Uri.encode(streamReferer);

            Map<String, String> headers = new HashMap<>();
            if (!streamReferer.isEmpty()) {
                headers.put("Referer", streamReferer);
            }

            DefaultHttpDataSource.Factory httpDataSourceFactory = new DefaultHttpDataSource.Factory()
                    .setDefaultRequestProperties(headers)
                    .setAllowCrossProtocolRedirects(true)
                    .setConnectTimeoutMs(15000)
                    .setReadTimeoutMs(30000)
                    .setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0");

            String epTitle = (title != null && !title.isEmpty()) ? (title + " - Ep " + ep) : ("Episode " + ep);
            androidx.media3.common.MediaMetadata mediaMetadata = new androidx.media3.common.MediaMetadata.Builder()
                    .setTitle(epTitle)
                    .setDisplayTitle(epTitle)
                    .setArtist(title != null ? title : "")
                    .build();

            MediaItem.Builder mib = new MediaItem.Builder()
                    .setUri(Uri.parse(proxiedVideo))
                    .setMediaMetadata(mediaMetadata);
            hasAppliedTrackSelectionForStream = false;

            if (isHls) {
                mib.setMimeType(MimeTypes.APPLICATION_M3U8);
                HlsMediaSource videoSource = new HlsMediaSource.Factory(httpDataSourceFactory)
                        .setAllowChunklessPreparation(true)
                        .createMediaSource(mib.build());
                player.setMediaSource(videoSource);
            } else {
                androidx.media3.exoplayer.source.ProgressiveMediaSource videoSource =
                        new androidx.media3.exoplayer.source.ProgressiveMediaSource.Factory(httpDataSourceFactory)
                                .createMediaSource(mib.build());
                player.setMediaSource(videoSource);
            }

            if (isHls) {
                applyHlsTrackSelection(activeQuality);
            }

            player.prepare();
            player.play();

            applySubtitleSelection();
        } catch (Throwable t) {
            if (layoutBuffering != null) layoutBuffering.setVisibility(View.GONE);
            Toast.makeText(this, "Gagal memutar video: " + t.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void applySubtitleSelection() {
        applySubtitleSelection(false);
    }

    private void applySubtitleSelection(boolean forceRefresh) {
        updateSubStatusText(false);
        updateExoButtonStates();

        if (!subEnabled || activeSubUrl == null || activeSubUrl.isEmpty()) {
            currentCues = new ArrayList<>();
            runOnUiThread(() -> {
                if (tvSubtitles != null) {
                    tvSubtitles.setText("");
                    tvSubtitles.setVisibility(View.GONE);
                }
            });
            return;
        }

        try {
            if (forceRefresh) {
                currentCues = new ArrayList<>();
            }
            String subModeParam = activeEngine.equals("raw") ? "" : activeEngine;
            String srcParam = activeEngine.equals("raw") ? activeSubLang : "en";

            String effectiveRef = streamReferer != null ? streamReferer : "";
            if (effectiveRef.isEmpty() && activeSubUrl != null) {
                String subLower = activeSubUrl.toLowerCase();
                if (subLower.contains("broforgotsave") || subLower.contains("stellarfrontier") || subLower.contains("megaplay") || subLower.contains("megacloud")) {
                    effectiveRef = "https://megaplay.buzz/";
                }
            }
            String encodedSubUrl = URLEncoder.encode(activeSubUrl, "UTF-8");
            String encodedRef = URLEncoder.encode(effectiveRef, "UTF-8");

            // Jika memilih terjemahan (AIGTX / AI / GTX) dan cues belum dimuat:
            // Unduh dulu subtitle sumber (English/Native) secara instan (0.5s) agar penonton tidak mengalami black screen / tanpa sub.
            if (!subModeParam.isEmpty() && currentCues.isEmpty() && enSourceSubUrl != null && !enSourceSubUrl.isEmpty() && !forceRefresh) {
                String rawSubUrl = "http://127.0.0.1:8767/api/player/sub?url=" + URLEncoder.encode(enSourceSubUrl, "UTF-8")
                        + "&referer=" + encodedRef
                        + "&src=" + URLEncoder.encode(srcParam, "UTF-8")
                        + "&lang=" + URLEncoder.encode(srcParam, "UTF-8");
                loadSubtitlesAsync(rawSubUrl, true);
            }

            // Bangun URL utama untuk terjemahan atau subtitle yang dipilih
            String proxiedSub = "http://127.0.0.1:8767/api/player/sub?url=" + encodedSubUrl
                    + "&referer=" + encodedRef
                    + "&src=" + URLEncoder.encode(srcParam, "UTF-8")
                    + "&lang=" + URLEncoder.encode(activeSubLang, "UTF-8")
                    + (subModeParam.isEmpty() ? "" : "&mode=" + URLEncoder.encode(subModeParam, "UTF-8"))
                    + (forceRefresh ? "&refresh=true" : "");

            loadSubtitlesAsync(proxiedSub, false);
        } catch (Exception e) {
            updateSubStatusText(false);
            if (tvSubStatus != null) {
                tvSubStatus.setText("Sub: Gagal (" + e.getMessage() + ")");
            }
        }
    }

    private void loadSubtitlesAsync(String subUrl, boolean isImmediateFallback) {
        final int loadId = ++currentSubLoadId;
        new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) new URL(subUrl).openConnection();
                conn.setConnectTimeout(15000);
                // Beri waktu cukup (80 detik) bila translasi baru pertama kali dijalankan
                conn.setReadTimeout(isImmediateFallback ? 12000 : 80000);
                conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0");
                conn.setInstanceFollowRedirects(true);

                int respCode = conn.getResponseCode();
                if (respCode >= 400) {
                    throw new Exception("HTTP " + respCode);
                }

                String trTier = conn.getHeaderField("X-Translate-Tier");
                String trErr = conn.getHeaderField("X-Translate-Error");

                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append("\n");
                }
                reader.close();

                if (loadId != currentSubLoadId && !isImmediateFallback) return; // Stale request

                List<SubtitleCue> cues = parseVtt(sb.toString());
                if (!cues.isEmpty()) {
                    if (isImmediateFallback) {
                        // Jangan timpa cues terjemahan jika cues utama sudah terisi
                        if (currentCues.isEmpty()) {
                            currentCues = cues;
                            runOnUiThread(() -> subtitleSyncRunnable.run());
                        }
                    } else {
                        currentCues = cues;
                        runOnUiThread(() -> {
                            boolean isFallbackTier = "source".equalsIgnoreCase(trTier) || "source-fallback".equalsIgnoreCase(trTier);
                            if (isFallbackTier) {
                                if (tvSubStatus != null) {
                                    tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " [Terjemahan Gagal, Teks Asli]");
                                }
                            } else {
                                updateSubStatusText(true);
                            }
                            subtitleSyncRunnable.run();
                        });
                    }
                }
            } catch (Exception e) {
                if (!isImmediateFallback && loadId == currentSubLoadId) {
                    runOnUiThread(() -> {
                        // Jika sudah ada cues (misal dari immediate source), jangan kosongkan layar!
                        if (!currentCues.isEmpty()) {
                            tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " [Menggunakan teks asli]");
                        } else {
                            updateSubStatusText(false);
                            if (tvSubStatus != null) {
                                tvSubStatus.setText("Sub: Gagal (" + e.getMessage() + ")");
                            }
                        }
                    });
                }
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        }).start();
    }

    private void updateSubStatusText(boolean isLoaded) {
        if (tvSubStatus == null) return;
        if (!subEnabled || activeSubUrl == null || activeSubUrl.isEmpty()) {
            if ("dub".equalsIgnoreCase(activeStreamMode) || (activeSubUrl == null || activeSubUrl.isEmpty())) {
                tvSubStatus.setText("Audio: English Dub (Tanpa Subtitle)");
            } else {
                tvSubStatus.setText("Subtitle: Nonaktif");
            }
            return;
        }
        String engineLabel = "Google GTX (Cepat)";
        if ("gtx+".equals(activeEngine) || "aigtx".equals(activeEngine)) engineLabel = "GTX+ (Smart Fansub & Scene Detection)";
        else if ("ai".equals(activeEngine)) engineLabel = "AI Fansub (" + configuredAiModel + ")";
        else if ("raw".equals(activeEngine)) {
            if ("en".equals(activeSubLang)) engineLabel = "Source English";
            else if ("id".equals(activeSubLang)) engineLabel = "Asli / Resmi";
            else engineLabel = "Source Asli";
        }

        String suffix = isLoaded ? "" : " [Memuat...]";
        tvSubStatus.setText("Sub: " + activeSubLang.toUpperCase() + " • " + engineLabel + suffix);
    }

    private static long parseTimestamp(String token) {
        if (token == null) return -1;
        token = token.trim();
        // Hapus WebVTT settings di baris waktu (misal align:start position:0%)
        int spaceIdx = -1;
        for (int i = 0; i < token.length(); i++) {
            char c = token.charAt(i);
            if (c == ' ' || c == '\t') {
                spaceIdx = i;
                break;
            }
        }
        if (spaceIdx != -1) {
            token = token.substring(0, spaceIdx).trim();
        }
        token = token.replace(',', '.');
        String[] parts = token.split(":");
        try {
            if (parts.length == 3) {
                long h = Long.parseLong(parts[0].trim());
                long m = Long.parseLong(parts[1].trim());
                double s = Double.parseDouble(parts[2].trim());
                return (long) ((h * 3600 + m * 60 + s) * 1000);
            } else if (parts.length == 2) {
                long m = Long.parseLong(parts[0].trim());
                double s = Double.parseDouble(parts[1].trim());
                return (long) ((m * 60 + s) * 1000);
            }
        } catch (Exception ignored) {}
        return -1;
    }

    private List<SubtitleCue> parseVtt(String content) {
        List<SubtitleCue> list = new ArrayList<>();
        if (content == null || content.isEmpty()) return list;

        // Buang BOM jika ada
        if (content.startsWith("\uFEFF")) {
            content = content.substring(1);
        }

        String[] lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n");
        long curStart = -1;
        long curEnd = -1;
        StringBuilder curText = new StringBuilder();

        for (String rawLine : lines) {
            String line = rawLine.trim();

            if (line.contains("-->")) {
                // Simpan cue sebelumnya jika belum sempat ter-flush
                if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
                    String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
                    if (!cleaned.isEmpty()) {
                        list.add(new SubtitleCue(curStart, curEnd, cleaned));
                    }
                    curText.setLength(0);
                }

                String[] timeParts = line.split("-->");
                if (timeParts.length >= 2) {
                    curStart = parseTimestamp(timeParts[0]);
                    curEnd = parseTimestamp(timeParts[1]);
                }
            } else if (line.isEmpty()) {
                if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
                    String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
                    if (!cleaned.isEmpty()) {
                        list.add(new SubtitleCue(curStart, curEnd, cleaned));
                    }
                }
                curStart = -1;
                curEnd = -1;
                curText.setLength(0);
            } else if (curStart != -1 && curEnd != -1) {
                // Abaikan header atau komentar WebVTT
                if (!line.startsWith("NOTE") && !line.startsWith("STYLE") && !line.startsWith("REGION")) {
                    if (curText.length() > 0) curText.append("\n");
                    curText.append(line);
                }
            }
        }

        if (curStart != -1 && curEnd != -1 && curText.length() > 0) {
            String cleaned = curText.toString().replaceAll("<[^>]*>", "").trim();
            if (!cleaned.isEmpty()) {
                list.add(new SubtitleCue(curStart, curEnd, cleaned));
            }
        }
        return list;
    }

    private SubtitleCue findActiveCue(long posMs) {
        List<SubtitleCue> cues = currentCues;
        if (cues == null || cues.isEmpty()) return null;
        int low = 0;
        int high = cues.size() - 1;
        int best = -1;
        while (low <= high) {
            int mid = (low + high) >>> 1;
            SubtitleCue cue = cues.get(mid);
            if (cue.startMs <= posMs) {
                best = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        if (best != -1) {
            SubtitleCue c = cues.get(best);
            if (posMs <= c.endMs) return c;
        }
        return null;
    }

    private void showQualitySelectorDialog() {
        if (streamVariants.isEmpty()) {
            Toast.makeText(this, "Hanya satu kualitas resolusi tersedia untuk video ini", Toast.LENGTH_SHORT).show();
            return;
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pilih Resolusi Video");

        List<String> options = new ArrayList<>();
        int selectedIdx = 0;
        for (int i = 0; i < streamVariants.size(); i++) {
            JSONObject v = streamVariants.get(i);
            String q = v.optString("q", "auto");
            boolean isCurrent = q.equalsIgnoreCase(activeQuality)
                    || (rawStreamUrl.equals(v.optString("url", "")) && !rawStreamUrl.isEmpty());
            if (isCurrent) selectedIdx = i;
            options.add(q.toUpperCase() + (isCurrent ? " [Aktif]" : ""));
        }

        builder.setSingleChoiceItems(options.toArray(new String[0]), selectedIdx, (dialog, which) -> {
            if (which >= 0 && which < streamVariants.size()) {
                JSONObject picked = streamVariants.get(which);
                String newQ = picked.optString("q", "auto");
                String newUrl = picked.optString("url", "");
                dialog.dismiss();
                switchQuality(newQ, newUrl);
            }
        });

        builder.setNegativeButton("Batal", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnQuality != null && btnQuality.getVisibility() == View.VISIBLE) {
                    btnQuality.requestFocus();
                } else if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void switchQuality(String newQ, String newUrl) {
        if (newQ == null || newQ.isEmpty()) return;
        activeQuality = newQ;
        if (btnQuality != null) {
            btnQuality.setText(newQ.toUpperCase());
        }
        getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE)
                .edit().putString("pref_quality", newQ).apply();

        hasFallbackAttempted = false;
        Toast.makeText(this, "Mengubah resolusi ke " + newQ.toUpperCase(), Toast.LENGTH_SHORT).show();

        boolean isHls = isHlsMode || isHlsStream(rawStreamUrl) || isHlsStream(masterStreamUrl);

        if (isHls && player != null) {
            long resumePos = player.getCurrentPosition();
            boolean wasPlaying = player.isPlaying();

            hasAppliedTrackSelectionForStream = true;
            applyHlsTrackSelection(newQ);

            // Khusus Android TV: True Seamless Quality Switching
            // Tidak memanggil player.stop() atau player.prepare() agar pemutaran tidak terputus (tanpa black screen/spinner).
            // SurfaceView dan hardware decoder otomatis menyesuaikan dimensi buffer pada batas segmen/GOP berikutnya.
            if (TvFocusHelper.isTv(this)) {
                if (playerView != null) {
                    playerView.setResizeMode(currentResizeMode);
                    View sv = playerView.getVideoSurfaceView();
                    if (sv != null) {
                        sv.requestLayout();
                    }
                    playerView.requestLayout();
                }
                return;
            }

            // Pada Android Mobile: Pertahankan alokasi/perilaku bawaan yang ada (100% UNTOUCHED)
            player.stop();
            if (resumePos > 0) {
                player.seekTo(resumePos);
            }
            player.prepare();
            if (wasPlaying) {
                player.play();
            }

            if (playerView != null) {
                playerView.setResizeMode(currentResizeMode);
                View sv = playerView.getVideoSurfaceView();
                if (sv != null) {
                    sv.requestLayout();
                }
                playerView.requestLayout();
            }
            return;
        }

        // Jalur non-HLS (Progressive MP4 tunggal): reload stream dengan URL baru
        if (newUrl == null || newUrl.isEmpty() || newUrl.equals(rawStreamUrl)) return;
        long resumePos = player != null ? player.getCurrentPosition() : 0;
        boolean wasPlaying = player != null && player.isPlaying();

        rawStreamUrl = newUrl;
        isHlsMode = isHlsStream(newUrl);

        applyCurrentStream();

        if (player != null) {
            androidx.media3.common.TrackSelectionParameters params = player.getTrackSelectionParameters().buildUpon()
                    .clearVideoSizeConstraints()
                    .clearOverridesOfType(androidx.media3.common.C.TRACK_TYPE_VIDEO)
                    .build();
            player.setTrackSelectionParameters(params);

            if (resumePos > 0) {
                player.seekTo(resumePos);
                if (wasPlaying) {
                    player.play();
                }
            }
        }

        if (playerView != null) {
            playerView.setResizeMode(currentResizeMode);
            View sv = playerView.getVideoSurfaceView();
            if (sv != null) {
                sv.requestLayout();
            }
            playerView.requestLayout();
        }
    }

    private void applyHlsTrackSelection(String quality) {
        if (player == null) return;
        if (quality == null || quality.isEmpty()) quality = "best";

        androidx.media3.common.TrackSelectionParameters.Builder builder =
                player.getTrackSelectionParameters().buildUpon()
                        .clearOverridesOfType(androidx.media3.common.C.TRACK_TYPE_VIDEO)
                        .clearVideoSizeConstraints();

        if (!"auto".equalsIgnoreCase(quality)) {
            int targetH = 1080;
            if ("best".equalsIgnoreCase(quality) || "hd".equalsIgnoreCase(quality) || quality.contains("1080")) {
                targetH = 1080;
            } else if (quality.contains("720")) {
                targetH = 720;
            } else if (quality.contains("480")) {
                targetH = 480;
            } else if (quality.contains("360")) {
                targetH = 360;
            }

            androidx.media3.common.Tracks currentTracks = player.getCurrentTracks();
            androidx.media3.common.TrackGroup targetGroup = null;
            int targetIndex = -1;
            int bestDiff = Integer.MAX_VALUE;

            for (androidx.media3.common.Tracks.Group group : currentTracks.getGroups()) {
                if (group.getType() == androidx.media3.common.C.TRACK_TYPE_VIDEO) {
                    androidx.media3.common.TrackGroup tg = group.getMediaTrackGroup();
                    for (int i = 0; i < tg.length; i++) {
                        androidx.media3.common.Format format = tg.getFormat(i);
                        int diff = Math.abs(format.height - targetH);
                        if (diff < bestDiff) {
                            bestDiff = diff;
                            targetGroup = tg;
                            targetIndex = i;
                        }
                    }
                }
            }

            if (targetGroup != null && targetIndex != -1) {
                builder.addOverride(new androidx.media3.common.TrackSelectionOverride(targetGroup, targetIndex));
            } else {
                int maxH = Integer.MAX_VALUE;
                int maxW = Integer.MAX_VALUE;
                if ("best".equalsIgnoreCase(quality) || "hd".equalsIgnoreCase(quality) || quality.contains("1080")) {
                    maxH = 1080; maxW = 1920;
                } else if (quality.contains("720")) {
                    maxH = 720; maxW = 1280;
                } else if (quality.contains("480")) {
                    maxH = 480; maxW = 854;
                } else if (quality.contains("360")) {
                    maxH = 360; maxW = 640;
                }

                builder.setMaxVideoSize(maxW, maxH);
            }
        }

        androidx.media3.common.TrackSelectionParameters newParams = builder.build();
        if (!newParams.equals(player.getTrackSelectionParameters())) {
            player.setTrackSelectionParameters(newParams);
        }
    }

    private void showSubtitleSelectorDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Subtitle & Mesin Terjemahan");

        List<String> options = new ArrayList<>();
        List<Runnable> actions = new ArrayList<>();

        if (enSourceSubUrl.isEmpty() && subtitleTracks.isEmpty()) {
            String msg = "dub".equalsIgnoreCase(activeStreamMode) ? "Audio: English Dub (Tidak ada file subtitle)" : "Tidak ada file subtitle untuk video ini";
            options.add("Peringatan: " + msg);
            actions.add(() -> {});
        } else {
            // 1. Google GTX Murni (Prioritas Pertama / Super Cepat)
            boolean isGtxSelected = subEnabled && "id".equals(activeSubLang) && "gtx".equals(activeEngine);
            options.add("[ID] Bahasa Indonesia (Google GTX Murni - Cepat)" + (isGtxSelected ? " [Aktif]" : ""));
            actions.add(() -> {
                subEnabled = true;
                activeSubLang = "id";
                activeEngine = "gtx";
                activeSubUrl = enSourceSubUrl;
            });

            // 2. GTX+ (Prioritas Kedua / GTX + Smart Fansub & Scene Detection)
            boolean isGtxPlusSelected = subEnabled && "id".equals(activeSubLang) && ("gtx+".equals(activeEngine) || "aigtx".equals(activeEngine));
            options.add("[ID] Bahasa Indonesia (GTX+ - Smart Fansub & Scene Detection)" + (isGtxPlusSelected ? " [Aktif]" : ""));
            actions.add(() -> {
                subEnabled = true;
                activeSubLang = "id";
                activeEngine = "gtx+";
                activeSubUrl = enSourceSubUrl;
            });

            // 3. AI Fansub (Prioritas Ketiga / LLM Translate)
            boolean isAiSelected = subEnabled && "id".equals(activeSubLang) && "ai".equals(activeEngine);
            String aiOptionText = "[AI] Bahasa Indonesia (AI Fansub / " + configuredAiModel + ")"
                    + (hasAiKey ? " [SIAP]" : " [Butuh Key]")
                    + (isAiSelected ? " [Aktif]" : "");
            options.add(aiOptionText);
            actions.add(() -> {
                subEnabled = true;
                activeSubLang = "id";
                activeEngine = "ai";
                activeSubUrl = enSourceSubUrl;
                if (!hasAiKey) {
                    Toast.makeText(this, "Perhatian: API Key AI belum disetel (:apikey <key> di home). Menggunakan GTX sebagai fallback otomatis.", Toast.LENGTH_LONG).show();
                }
            });

            // 4. Native Indonesian (jika tersedia di track asli)
            if (!idNativeSubUrl.isEmpty()) {
                boolean isIdNativeSelected = subEnabled && "id".equals(activeSubLang) && "raw".equals(activeEngine) && idNativeSubUrl.equals(activeSubUrl);
                options.add("[ID] Bahasa Indonesia (Asli / Bawaan)" + (isIdNativeSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "id";
                    activeEngine = "raw";
                    activeSubUrl = idNativeSubUrl;
                });
            }

            // 5. English (Original)
            if (!enSourceSubUrl.isEmpty()) {
                boolean isEnSelected = subEnabled && "en".equals(activeSubLang) && "raw".equals(activeEngine);
                options.add("[EN] English (Original / Asli)" + (isEnSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = "en";
                    activeEngine = "raw";
                    activeSubUrl = enSourceSubUrl;
                });
            }

            // 6. Daftar track bahasa lain yang tersedia (misal Spanish, French, Japanese, dsb.)
            for (int i = 0; i < subtitleTracks.size(); i++) {
                JSONObject s = subtitleTracks.get(i);
                String url = s.optString("url", "");
                String lbl = s.optString("label", "Track " + (i + 1));
                String lang = s.optString("lang", "").toLowerCase();
                // Lewati track English & ID native karena sudah disediakan di menu utama di atas
                if (url.equals(enSourceSubUrl) || url.equals(idNativeSubUrl)) {
                    continue;
                }
                boolean isThisSelected = subEnabled && "raw".equals(activeEngine) && url.equals(activeSubUrl);
                options.add(lbl + (isThisSelected ? " [Aktif]" : ""));
                actions.add(() -> {
                    subEnabled = true;
                    activeSubLang = lang.isEmpty() ? "en" : lang;
                    activeEngine = "raw";
                    activeSubUrl = url;
                });
            }
        }

        // Opsi Muat Ulang / Terjemahkan Ulang Subtitle (Hapus Cache)
        if (subEnabled && !"raw".equals(activeEngine)) {
            options.add("[Refresh] Terjemahkan Ulang Subtitle (Hapus Cache)");
            actions.add(() -> {
                Toast.makeText(this, "Menerjemahkan ulang subtitle dari awal...", Toast.LENGTH_SHORT).show();
                applySubtitleSelection(true);
            });
        }

        // 7. Pengaturan Tampilan & Gaya Subtitle
        options.add("Pengaturan Tampilan (Posisi, Latar Belakang & Ukuran)...");
        actions.add(this::showSubtitleStyleDialog);

        // 8. Matikan Subtitle
        options.add("Matikan Subtitle" + (!subEnabled ? " [Aktif]" : ""));
        actions.add(() -> {
            subEnabled = false;
        });

        builder.setItems(options.toArray(new String[0]), (dialog, which) -> {
            if (which >= 0 && which < actions.size()) {
                String chosen = options.get(which);
                actions.get(which).run();
                if (!chosen.contains("[Refresh]")) {
                    getSharedPreferences("tatap_player_prefs", MODE_PRIVATE).edit()
                            .putString("pref_sub_engine", activeEngine)
                            .putString("pref_sub_lang", activeSubLang)
                            .putBoolean("pref_sub_enabled", subEnabled)
                            .apply();
                    applySubtitleSelection();
                    Toast.makeText(this, "Subtitle diperbarui: " + (subEnabled ? activeSubLang.toUpperCase() + " [" + activeEngine + "]" : "OFF"), Toast.LENGTH_SHORT).show();
                }
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnSubSelector != null && btnSubSelector.getVisibility() == View.VISIBLE) {
                    btnSubSelector.requestFocus();
                } else if (btnExoSub != null && btnExoSub.getVisibility() == View.VISIBLE) {
                    btnExoSub.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void applySubtitleStyle() {
        if (tvSubtitles == null) return;
        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
        boolean isTv = TvFocusHelper.isTv(this);
        String pos = sp.getString("sub_pos", "low");
        String bg = sp.getString("sub_bg", "subtle");
        String defaultSize = isTv ? "large" : "medium";
        String size = sp.getString("sub_size", defaultSize);

        // 1. Margin Bawah (Posisi)
        int marginDp = 22; // Default 22dp: Rendah & pas di batas bawah layar
        if ("mid".equals(pos)) marginDp = 36;
        else if ("high".equals(pos)) marginDp = 54;

        int marginPx = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, marginDp, getResources().getDisplayMetrics());
        ViewGroup.MarginLayoutParams lp = (ViewGroup.MarginLayoutParams) tvSubtitles.getLayoutParams();
        if (lp != null) {
            lp.bottomMargin = marginPx;
            tvSubtitles.setLayoutParams(lp);
        }

        // 2. Ukuran Font & Spasi Baris Dinamis (Adaptif Android TV vs Mobile)
        float sizeSp;
        if (isTv) {
            if ("small".equals(size)) sizeSp = 18f;
            else if ("medium".equals(size)) sizeSp = 22f;
            else if ("large".equals(size)) sizeSp = 26f; // Standar TV
            else if ("xlarge".equals(size)) sizeSp = 30f;
            else if ("xxlarge".equals(size)) sizeSp = 34f; // Jarak Jauh
            else if ("jumbo".equals(size)) sizeSp = 38f;  // Layar Besar
            else if ("max".equals(size)) sizeSp = 42f;    // Maksimal
            else sizeSp = 26f;
        } else {
            if ("small".equals(size)) sizeSp = 14f;
            else if ("medium".equals(size)) sizeSp = 17f; // Standar HP
            else if ("large".equals(size)) sizeSp = 21f;
            else if ("xlarge".equals(size)) sizeSp = 25f;
            else if ("xxlarge".equals(size)) sizeSp = 29f;
            else if ("jumbo".equals(size)) sizeSp = 33f;
            else if ("max".equals(size)) sizeSp = 36f;
            else sizeSp = 17f;
        }
        tvSubtitles.setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp);
        // Spasi baris proporsional agar kalimat multi-baris berukuran besar tidak tumpang tindih
        tvSubtitles.setLineSpacing(0f, isTv ? 1.25f : 1.15f);

        // 3. Latar Belakang & Shadow
        GradientDrawable gd = new GradientDrawable();
        int cornerPx = (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, isTv ? 8 : 6, getResources().getDisplayMetrics());
        gd.setCornerRadius(cornerPx);

        if ("transparent".equals(bg)) {
            // Tanpa box background sama sekali, teks tebal dengan shadow tajam (gaya fansub modern)
            tvSubtitles.setBackground(null);
            tvSubtitles.setShadowLayer(isTv ? 8f : 6f, 2f, 2f, 0xFF000000);
        } else {
            int bgColor = 0x4D000000; // 30% alpha (samar & lembut, tidak pekat)
            if ("medium".equals(bg)) bgColor = 0x8C000000; // 55%
            else if ("dark".equals(bg)) bgColor = 0xCC000000; // 80% pekat
            gd.setColor(bgColor);
            tvSubtitles.setBackground(gd);
            tvSubtitles.setShadowLayer(isTv ? 6f : 4f, 1.5f, 1.5f, 0xFF000000);
        }
    }

    private void showSubtitleStyleDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Tampilan Subtitle");

        SharedPreferences sp = getSharedPreferences("tatap_player_prefs", Context.MODE_PRIVATE);
        boolean isTv = TvFocusHelper.isTv(this);
        String curPos = sp.getString("sub_pos", "low");
        String curBg = sp.getString("sub_bg", "subtle");
        String defaultSize = isTv ? "large" : "medium";
        String curSize = sp.getString("sub_size", defaultSize);

        String posLabel = "low".equals(curPos) ? "Bawah (22dp) [Pas]" : ("mid".equals(curPos) ? "Sedang (36dp)" : "Tinggi (54dp)");
        String bgLabel = "transparent".equals(curBg) ? "Transparan (Tanpa Box)" : ("subtle".equals(curBg) ? "Samar / Lembut (30%)" : ("medium".equals(curBg) ? "Sedang (55%)" : "Pekat (80%)"));

        String sizeLabel;
        if (isTv) {
            if ("small".equals(curSize)) sizeLabel = "Kecil (18sp)";
            else if ("medium".equals(curSize)) sizeLabel = "Sedang (22sp)";
            else if ("large".equals(curSize)) sizeLabel = "Besar (26sp) [Standar TV]";
            else if ("xlarge".equals(curSize)) sizeLabel = "Sangat Besar (30sp)";
            else if ("xxlarge".equals(curSize)) sizeLabel = "Ekstra Besar (34sp) [Jarak Jauh]";
            else if ("jumbo".equals(curSize)) sizeLabel = "Jumbo (38sp) [Layar Besar]";
            else if ("max".equals(curSize)) sizeLabel = "Maksimal (42sp)";
            else sizeLabel = "Besar (26sp)";
        } else {
            if ("small".equals(curSize)) sizeLabel = "Kecil (14sp)";
            else if ("medium".equals(curSize)) sizeLabel = "Sedang (17sp) [Standar HP]";
            else if ("large".equals(curSize)) sizeLabel = "Besar (21sp)";
            else if ("xlarge".equals(curSize)) sizeLabel = "Sangat Besar (25sp)";
            else if ("xxlarge".equals(curSize)) sizeLabel = "Ekstra Besar (29sp)";
            else if ("jumbo".equals(curSize)) sizeLabel = "Jumbo (33sp)";
            else if ("max".equals(curSize)) sizeLabel = "Maksimal (36sp)";
            else sizeLabel = "Sedang (17sp)";
        }

        String[] menu = new String[]{
                "Posisi Subtitle: " + posLabel,
                "Latar Belakang: " + bgLabel,
                "Ukuran Huruf: " + sizeLabel,
                "Reset ke Default"
        };

        builder.setItems(menu, (dialog, which) -> {
            if (which == 0) {
                showPositionPicker(sp);
            } else if (which == 1) {
                showBackgroundPicker(sp);
            } else if (which == 2) {
                showSizePicker(sp);
            } else if (which == 3) {
                sp.edit().putString("sub_pos", "low").putString("sub_bg", "subtle").putString("sub_size", defaultSize).apply();
                applySubtitleStyle();
                Toast.makeText(this, "Tampilan subtitle direset ke default", Toast.LENGTH_SHORT).show();
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnSubStyle != null && btnSubStyle.getVisibility() == View.VISIBLE) {
                    btnSubStyle.requestFocus();
                } else if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                }
            }
        });
        builder.show();
    }

    private void showPositionPicker(SharedPreferences sp) {
        String[] options = new String[]{
                "Bawah / Rendah (22dp) [Direkomendasikan]",
                "Sedang (36dp)",
                "Tinggi (54dp)"
        };
        String cur = sp.getString("sub_pos", "low");
        int checked = "high".equals(cur) ? 2 : ("mid".equals(cur) ? 1 : 0);

        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Posisi Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = which == 2 ? "high" : (which == 1 ? "mid" : "low");
                    sp.edit().putString("sub_pos", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Posisi subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    private void showBackgroundPicker(SharedPreferences sp) {
        String[] options = new String[]{
                "Transparan (Tanpa Box / Shadow Teks Bersih)",
                "Samar / Lembut (30% Alpha) [Direkomendasikan]",
                "Sedang (55% Alpha)",
                "Pekat (80% Alpha)"
        };
        String cur = sp.getString("sub_bg", "subtle");
        int checked = "transparent".equals(cur) ? 0 : ("medium".equals(cur) ? 2 : ("dark".equals(cur) ? 3 : 1));

        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Latar Belakang Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = which == 0 ? "transparent" : (which == 2 ? "medium" : (which == 3 ? "dark" : "subtle"));
                    sp.edit().putString("sub_bg", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Gaya latar subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    private void showSizePicker(SharedPreferences sp) {
        boolean isTv = TvFocusHelper.isTv(this);
        String defaultSize = isTv ? "large" : "medium";
        String cur = sp.getString("sub_size", defaultSize);

        String[] options;
        String[] values;

        if (isTv) {
            options = new String[]{
                    "Kecil (18sp)",
                    "Sedang (22sp)",
                    "Besar (26sp) [Standar TV]",
                    "Sangat Besar (30sp)",
                    "Ekstra Besar (34sp) [Jarak Jauh 3.5m+]",
                    "Jumbo (38sp) [Layar Besar 55\"-75\"]",
                    "Maksimal (42sp) [Visibilitas Tinggi]"
            };
            values = new String[]{"small", "medium", "large", "xlarge", "xxlarge", "jumbo", "max"};
        } else {
            options = new String[]{
                    "Kecil (14sp)",
                    "Sedang (17sp) [Standar HP]",
                    "Besar (21sp)",
                    "Sangat Besar (25sp)",
                    "Ekstra Besar (29sp)",
                    "Jumbo (33sp)",
                    "Maksimal (36sp)"
            };
            values = new String[]{"small", "medium", "large", "xlarge", "xxlarge", "jumbo", "max"};
        }

        int checked = 2; // Default "large" di TV
        if (!isTv) checked = 1; // Default "medium" di HP
        for (int i = 0; i < values.length; i++) {
            if (values[i].equals(cur)) {
                checked = i;
                break;
            }
        }

        final String[] finalValues = values;
        new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert)
                .setTitle("Pilih Ukuran Huruf Subtitle")
                .setSingleChoiceItems(options, checked, (dialog, which) -> {
                    String val = (which >= 0 && which < finalValues.length) ? finalValues[which] : defaultSize;
                    sp.edit().putString("sub_size", val).apply();
                    applySubtitleStyle();
                    dialog.dismiss();
                    Toast.makeText(this, "Ukuran subtitle disimpan", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Batal", null)
                .show();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (player != null) player.pause();
        handler.removeCallbacks(subtitleSyncRunnable);
        handler.removeCallbacks(preResolveRunnable);
    }

    @Override
    protected void onResume() {
        super.onResume();
        hideSystemUi();
        if (player != null && player.isPlaying()) {
            handler.removeCallbacks(subtitleSyncRunnable);
            handler.post(subtitleSyncRunnable);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        handler.removeCallbacks(subtitleSyncRunnable);
        handler.removeCallbacks(preResolveRunnable);
        if (player != null) {
            player.release();
            player = null;
        }
    }

    private void setupExoNativeControls() {
        if (playerView == null) return;
        playerView.post(() -> {
            bindExoControlButtons();
            updateExoButtonStates();
        });
    }

    private void bindExoControlButtons() {
        if (playerView == null) return;
        if (btnExoNext == null) {
            btnExoNext = playerView.findViewById(androidx.media3.ui.R.id.exo_next);
            if (btnExoNext != null) {
                btnExoNext.setOnClickListener(v -> playNextEpisode());
                TvFocusHelper.attachFocusScale(btnExoNext, 1.15f, 6f);
            }
        }
        if (btnExoPrev == null) {
            btnExoPrev = playerView.findViewById(androidx.media3.ui.R.id.exo_prev);
            if (btnExoPrev != null) {
                btnExoPrev.setOnClickListener(v -> playPrevEpisode());
                TvFocusHelper.attachFocusScale(btnExoPrev, 1.15f, 6f);
            }
        }
        if (btnExoSub == null) {
            btnExoSub = playerView.findViewById(androidx.media3.ui.R.id.exo_subtitle);
            if (btnExoSub != null) {
                btnExoSub.setVisibility(View.VISIBLE);
                btnExoSub.setOnClickListener(v -> showSubtitleSelectorDialog());
                TvFocusHelper.attachFocusScale(btnExoSub, 1.15f, 6f);
            }
        }
        if (btnExoSettings == null) {
            btnExoSettings = playerView.findViewById(androidx.media3.ui.R.id.exo_settings);
            if (btnExoSettings != null) {
                btnExoSettings.setVisibility(View.VISIBLE);
                btnExoSettings.setOnClickListener(v -> showPlayerUnifiedSettingsDialog());
                TvFocusHelper.attachFocusScale(btnExoSettings, 1.15f, 6f);
            }
        }
        if (btnExoFullscreen == null) {
            btnExoFullscreen = playerView.findViewById(androidx.media3.ui.R.id.exo_fullscreen);
            if (btnExoFullscreen != null) {
                btnExoFullscreen.setVisibility(View.VISIBLE);
                btnExoFullscreen.setOnClickListener(v -> cycleAspectRatio());
                TvFocusHelper.attachFocusScale(btnExoFullscreen, 1.15f, 6f);
            }
        }
    }

    private void updateExoButtonStates() {
        runOnUiThread(() -> {
            bindExoControlButtons();
            boolean hasNext = hasNextEpisode();
            boolean hasPrev = hasPrevEpisode();

            if (btnExoNext != null) {
                btnExoNext.setEnabled(hasNext);
                btnExoNext.setFocusable(hasNext);
                btnExoNext.setAlpha(hasNext ? 1.0f : 0.35f);
            }
            if (btnExoPrev != null) {
                btnExoPrev.setEnabled(hasPrev);
                btnExoPrev.setFocusable(hasPrev);
                btnExoPrev.setAlpha(hasPrev ? 1.0f : 0.35f);
            }
            if (btnExoSub != null) {
                btnExoSub.setAlpha(subEnabled ? 1.0f : 0.45f);
            }
            if (btnSubSelector != null) {
                btnSubSelector.setAlpha(subEnabled ? 1.0f : 0.6f);
            }
        });
    }

    private void showPlayerUnifiedSettingsDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
        builder.setTitle("Pengaturan Pemutar");

        String qLabel = activeQuality != null && !activeQuality.isEmpty() ? activeQuality.toUpperCase() : "AUTO";
        String subLabel = !subEnabled ? "Mati" : (activeSubLang.toUpperCase() + " [" + activeEngine + "]");
        String[] menu = new String[]{
                "Pilihan Subtitle & Terjemahan (" + subLabel + ")",
                "Pilihan Kualitas Video (" + qLabel + ")",
                "Pengaturan Tampilan & Gaya Subtitle",
                "Skala Layar / Rasio Aspek (" + getAspectLabel() + ")"
        };

        builder.setItems(menu, (dialog, which) -> {
            if (which == 0) {
                showSubtitleSelectorDialog();
            } else if (which == 1) {
                showQualitySelectorDialog();
            } else if (which == 2) {
                showSubtitleStyleDialog();
            } else if (which == 3) {
                cycleAspectRatio();
            }
        });

        builder.setNegativeButton("Tutup", (dialog, which) -> dialog.dismiss());
        builder.setOnDismissListener(dialog -> {
            if (playerView != null) {
                playerView.showController();
                if (btnExoSettings != null && btnExoSettings.getVisibility() == View.VISIBLE) {
                    btnExoSettings.requestFocus();
                } else if (btnQuality != null && btnQuality.getVisibility() == View.VISIBLE) {
                    btnQuality.requestFocus();
                }
            }
        });
        builder.show();
    }

    private String getAspectLabel() {
        if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_ZOOM) {
            return "Zoom";
        } else if (currentResizeMode == AspectRatioFrameLayout.RESIZE_MODE_FILL) {
            return "Fill";
        } else {
            return "Fit";
        }
    }

    private void ensureEpisodeListLoaded() {
        if ((!episodeList.isEmpty() && episodeList.size() > 1) || isEpisodeListLoading || slug == null || slug.isEmpty()) return;
        isEpisodeListLoading = true;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/episodes";
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(12000);
                int code = conn.getResponseCode();
                InputStream is = (code >= 200 && code < 400) ? conn.getInputStream() : conn.getErrorStream();
                if (is != null) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                    StringBuilder sb = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) sb.append(line);
                    reader.close();
                    JSONObject res = new JSONObject(sb.toString());
                    if (res.optBoolean("success")) {
                        JSONArray epsArr = res.getJSONObject("data").getJSONArray("episodes");
                        List<Integer> list = new ArrayList<>();
                        for (int i = 0; i < epsArr.length(); i++) {
                            list.add(epsArr.getJSONObject(i).getInt("ep"));
                        }
                        java.util.Collections.sort(list);
                        runOnUiThread(() -> {
                            if (!list.isEmpty()) {
                                episodeList.clear();
                                episodeList.addAll(list);
                                updateExoButtonStates();
                                preResolveNeighbors();
                            }
                        });
                    }
                }
                conn.disconnect();
            } catch (Exception ignored) {}
            isEpisodeListLoading = false;
        }).start();
    }

    private boolean hasNextEpisode() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0) {
                return idx < episodeList.size() - 1;
            }
            for (int e : episodeList) {
                if (e > ep) return true;
            }
            return false;
        }
        return true;
    }

    private boolean hasPrevEpisode() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0) {
                return idx > 0;
            }
            for (int e : episodeList) {
                if (e < ep) return true;
            }
            return ep > 1;
        }
        return ep > 1;
    }

    private int getNextEpisodeNumber() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx >= 0 && idx < episodeList.size() - 1) {
                return episodeList.get(idx + 1);
            }
            for (int e : episodeList) {
                if (e > ep) return e;
            }
        }
        return ep + 1;
    }

    private int getPrevEpisodeNumber() {
        if (episodeList != null && !episodeList.isEmpty()) {
            int idx = episodeList.indexOf(ep);
            if (idx > 0) {
                return episodeList.get(idx - 1);
            }
            int prev = -1;
            for (int e : episodeList) {
                if (e < ep) {
                    if (prev == -1 || e > prev) prev = e;
                }
            }
            if (prev != -1) return prev;
        }
        return Math.max(1, ep - 1);
    }

    private void playNextEpisode() {
        int nextEp = getNextEpisodeNumber();
        switchEpisode(nextEp);
    }

    private void playPrevEpisode() {
        int prevEp = getPrevEpisodeNumber();
        switchEpisode(prevEp);
    }

    private void switchEpisode(int targetEp) {
        if (ep == targetEp) return;
        ep = targetEp;

        currentResolveLoadId++;
        final int thisResolveId = currentResolveLoadId;

        currentSubLoadId++;
        currentCues = new ArrayList<>();
        if (tvSubtitles != null) {
            tvSubtitles.setText("");
            tvSubtitles.setVisibility(View.GONE);
        }
        rawStreamUrl = "";
        activeSubUrl = "";
        masterStreamUrl = "";
        subtitleTracks.clear();
        hasFallbackAttempted = false;

        if (player != null) {
            player.stop();
            player.clearMediaItems();
        }

        if (title != null && !title.isEmpty()) {
            tvPlayerTitle.setText(title + " - Ep " + ep);
        } else {
            tvPlayerTitle.setText("Episode " + ep);
        }

        updateExoButtonStates();

        if (layoutBuffering != null) {
            layoutBuffering.setVisibility(View.VISIBLE);
            if (tvBufferingText != null) tvBufferingText.setText("MEMUAT EPISODE " + ep + "...");
        }

        // Rekam episode baru ke riwayat
        new Thread(() -> {
            try {
                JSONObject b = new JSONObject();
                b.put("slug", slug != null ? slug : "");
                b.put("title", title != null ? title : "");
                b.put("episode", ep);
                b.put("mode", "sub");
                b.put("progress", 0);

                HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:8767/api/history").openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(3000);
                java.io.OutputStream os = conn.getOutputStream();
                os.write(b.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                os.close();
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();

        resolveAndPlayStream(thisResolveId);
    }

    /**
     * Pre-resolve URL episode sebelum (N-1) dan sesudah (N+1) secara background.
     * ZERO VIDEO PRE-BUFFERING:
     * Hanya meminta metadata JSON stream/subtitle ke server backend lokal (yang akan
     * di-scrape & disimpan ke SQLite episode_cache). Tidak mengunduh segmen video .ts
     * atau buffer video ExoPlayer untuk menjaga konsumsi RAM dan kuota tetap minimal.
     */
    private final Runnable preResolveRunnable = this::executePreResolveNeighbors;

    private void preResolveNeighbors() {
        if (TvFocusHelper.isTv(this)) {
            // Pada TV, tunda preResolve 20 detik setelah pemutaran stabil agar tidak berebut CPU/RAM hardware decoder
            handler.removeCallbacks(preResolveRunnable);
            handler.postDelayed(preResolveRunnable, 20_000);
            return;
        }
        executePreResolveNeighbors();
    }

    private void executePreResolveNeighbors() {
        final String currentSlug = (slug != null) ? slug : "";
        final String currentQ = (activeQuality != null && !activeQuality.isEmpty()) ? activeQuality : "best";

        if (currentSlug.isEmpty()) return;

        List<Integer> targets = new ArrayList<>();
        if (hasNextEpisode()) {
            targets.add(getNextEpisodeNumber());
        }
        if (hasPrevEpisode()) {
            targets.add(getPrevEpisodeNumber());
        }

        if (targets.isEmpty()) return;

        new Thread(() -> {
            for (int targetEp : targets) {
                try {
                    String u = "http://127.0.0.1:8767/api/stream/resolve?slug="
                            + URLEncoder.encode(currentSlug, "UTF-8")
                            + "&ep=" + targetEp
                            + "&mode=sub&q=" + URLEncoder.encode(currentQ, "UTF-8");
                    HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(20000);
                    int respCode = conn.getResponseCode();
                    if (respCode == 200) {
                        BufferedReader r = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                        while (r.readLine() != null) {}
                        r.close();
                    }
                    conn.disconnect();
                } catch (Exception ignored) {}
            }
        }).start();
    }

    @Override
    public void onTrimMemory(int level) {
        super.onTrimMemory(level);
        if (level >= TRIM_MEMORY_RUNNING_LOW) {
            ImageLoader.trimMemory();
            if (TvFocusHelper.isTv(this)) {
                new Thread(() -> {
                    try {
                        Class<?> pyClass = Class.forName("com.chaquo.python.Python");
                        if ((Boolean) pyClass.getMethod("isStarted").invoke(null)) {
                            Object pyInstance = pyClass.getMethod("getInstance").invoke(null);
                            Object launcherMod = pyClass.getMethod("getModule", String.class).invoke(pyInstance, "server_launcher");
                            launcherMod.getClass().getMethod("callAttr", String.class, Object[].class).invoke(launcherMod, "trim_memory", new Object[]{});
                        }
                    } catch (Throwable ignored) {}
                }).start();
            }
        }
    }
}
