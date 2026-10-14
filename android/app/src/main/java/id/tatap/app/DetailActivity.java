package id.tatap.app;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.cardview.widget.CardView;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import com.google.android.material.card.MaterialCardView;

public class DetailActivity extends Activity {
    private String slug;
    private String title;
    private String poster;
    private String type;
    private String eps;
    private String sub;

    private TextView tvTitle, tvTitleFull, tvSlug, tvTypeBadge, btnStarFavorite;
    private boolean isFavorite = false;
    private ImageView ivPoster;
    private Button btnQuickPlay, btnSortOrder;
    private ProgressBar pbLoading;
    private RecyclerView rvEpisodes;
    private EpisodeAdapter adapter;

    private SharedPreferences prefs;
    private final List<Integer> originalEpisodes = new ArrayList<>();
    private boolean isAscending = true;

    private View layoutSeasons;
    private RecyclerView rvSeasons;
    private SeasonAdapter seasonAdapter;

    private RecyclerView rvEpisodeRanges;
    private RangeAdapter rangeAdapter;
    private EpisodeRange activeRange = null;

    static class EpisodeRange {
        final int start;
        final int end;
        final String label;
        final boolean isAll;

        EpisodeRange(int start, int end, String label, boolean isAll) {
            this.start = start;
            this.end = end;
            this.label = label;
            this.isAll = isAll;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_detail);

        slug = getIntent().getStringExtra("slug");
        title = getIntent().getStringExtra("title");
        poster = getIntent().getStringExtra("poster");
        type = getIntent().getStringExtra("type");
        eps = getIntent().getStringExtra("eps");
        sub = getIntent().getStringExtra("sub");

        prefs = getSharedPreferences("tatap_history", Context.MODE_PRIVATE);

        tvTitle = findViewById(R.id.tv_detail_title);
        tvTitleFull = findViewById(R.id.tv_detail_title_full);
        tvSlug = findViewById(R.id.tv_detail_slug);
        tvTypeBadge = findViewById(R.id.tv_detail_type_badge);
        ivPoster = findViewById(R.id.iv_detail_poster);
        btnQuickPlay = findViewById(R.id.btn_quick_play);
        btnSortOrder = findViewById(R.id.btn_sort_order);
        pbLoading = findViewById(R.id.pb_detail_loading);
        ImageButton btnBack = findViewById(R.id.btn_back);
        btnStarFavorite = findViewById(R.id.btn_star_favorite);
        rvEpisodes = findViewById(R.id.rv_episodes);
        layoutSeasons = findViewById(R.id.layout_detail_seasons);
        rvSeasons = findViewById(R.id.rv_detail_seasons);
        rvEpisodeRanges = findViewById(R.id.rv_episode_ranges);

        tvTitle.setText(title != null ? title : "Detail Anime");
        tvTitleFull.setText(title != null ? title : "Anime");

        String badgeText = (type != null && !type.isEmpty() ? type : "ANIME")
                + (eps != null && !eps.isEmpty() ? " · " + eps + " EP" : "")
                + (sub != null && !sub.isEmpty() ? " · " + sub : "");
        tvTypeBadge.setText(badgeText);
        tvSlug.setText("Memuat episode...");

        if (poster != null && !poster.isEmpty()) {
            ImageLoader.load(poster, ivPoster);
        }

        btnBack.setOnClickListener(v -> finish());
        TvFocusHelper.attachFocusScale(btnBack, 1.1f, 6f);
        TvFocusHelper.attachFocusScale(btnQuickPlay, 1.05f, 6f);
        TvFocusHelper.attachFocusScale(btnSortOrder, 1.05f, 6f);
        if (btnStarFavorite != null) {
            btnStarFavorite.setOnClickListener(v -> toggleFavorite());
            TvFocusHelper.attachFocusScale(btnStarFavorite, 1.15f, 6f);
        }

        int epSpan = getResources().getInteger(R.integer.episode_grid_columns);
        rvEpisodes.setLayoutManager(new GridLayoutManager(this, epSpan));
        adapter = new EpisodeAdapter();
        rvEpisodes.setAdapter(adapter);

        if (rvEpisodeRanges != null) {
            rvEpisodeRanges.setLayoutManager(new androidx.recyclerview.widget.LinearLayoutManager(this, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false));
            rangeAdapter = new RangeAdapter();
            rvEpisodeRanges.setAdapter(rangeAdapter);
        }

        if (rvSeasons != null) {
            rvSeasons.setLayoutManager(new androidx.recyclerview.widget.LinearLayoutManager(this, androidx.recyclerview.widget.LinearLayoutManager.HORIZONTAL, false));
            seasonAdapter = new SeasonAdapter();
            rvSeasons.setAdapter(seasonAdapter);
        }

        btnSortOrder.setOnClickListener(v -> {
            isAscending = !isAscending;
            btnSortOrder.setText(isAscending ? "1 - N" : "N - 1");
            updateEpisodeDisplay();
        });

        btnQuickPlay.setOnClickListener(v -> {
            int targetEp = prefs.getInt("last_ep_" + slug, -1);
            if (targetEp <= 0) {
                if (!originalEpisodes.isEmpty()) {
                    targetEp = originalEpisodes.get(0);
                } else {
                    targetEp = 1;
                }
            }
            playEpisode(targetEp);
        });

        updateQuickPlayButton();
        if (TvFocusHelper.isTv(this)) {
            btnQuickPlay.post(() -> btnQuickPlay.requestFocus());
        }
        loadEpisodes();
        loadRelations();
        loadFavoriteState();
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateQuickPlayButton();
        if (adapter != null) {
            adapter.notifyDataSetChanged();
        }
    }

    private void updateQuickPlayButton() {
        int lastEp = prefs.getInt("last_ep_" + slug, -1);
        if (lastEp > 0) {
            btnQuickPlay.setText("Lanjutkan Ep " + lastEp);
            btnQuickPlay.setBackgroundColor(0xFF1E2433);
        } else {
            btnQuickPlay.setText("Putar Ep 1");
            btnQuickPlay.setBackgroundColor(0xFF161922);
        }
    }

    private void playEpisode(int ep) {
        prefs.edit()
                .putInt("last_ep_" + slug, ep)
                .putBoolean("watched_" + slug + "_" + ep, true)
                .apply();

        // Rekam riwayat tontonan ke backend lokal
        new Thread(() -> {
            try {
                JSONObject b = new JSONObject();
                b.put("slug", slug);
                b.put("title", title != null ? title : slug);
                b.put("episode", ep);
                b.put("poster", poster != null ? poster : "");
                b.put("type", type != null ? type : "");
                b.put("mode", "sub");

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

        Intent intent = new Intent(DetailActivity.this, PlayerActivity.class);
        intent.putExtra("slug", slug);
        intent.putExtra("ep", ep);
        intent.putExtra("title", title);
        intent.putExtra("poster", poster);
        intent.putExtra("type", type);
        intent.putIntegerArrayListExtra("episode_list", new ArrayList<>(originalEpisodes));
        startActivity(intent);
    }

    private void loadEpisodes() {
        if (pbLoading != null) pbLoading.setVisibility(View.VISIBLE);
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/episodes";
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
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
                    Collections.sort(list);
                    runOnUiThread(() -> {
                        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                        originalEpisodes.clear();
                        originalEpisodes.addAll(list);
                        tvSlug.setText(list.size() + " Episode Tersedia");
                        setupEpisodeRanges(list);
                        updateEpisodeDisplay();
                        updateQuickPlayButton();
                    });
                } else {
                    runOnUiThread(() -> {
                        if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                        tvSlug.setText("Episode tidak ditemukan");
                    });
                }
            } catch (Exception e) {
                runOnUiThread(() -> {
                    if (pbLoading != null) pbLoading.setVisibility(View.GONE);
                    Toast.makeText(this, "Gagal memuat episode: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    tvSlug.setText("Gagal terhubung ke backend");
                });
            }
        }).start();
    }

    private void setupEpisodeRanges(List<Integer> list) {
        if (rvEpisodeRanges == null) return;
        if (list != null && list.size() > 100) {
            rvEpisodeRanges.setVisibility(View.VISIBLE);
            List<EpisodeRange> ranges = new ArrayList<>();
            int total = list.size();
            int step = 100;
            for (int s = 1; s <= total; s += step) {
                int e = Math.min(s + step - 1, total);
                ranges.add(new EpisodeRange(s, e, s + " - " + e, false));
            }
            ranges.add(new EpisodeRange(1, total, "Semua (" + total + ")", true));

            int lastPlayedEp = prefs.getInt("last_ep_" + slug, -1);
            activeRange = ranges.get(0);
            if (lastPlayedEp > 0) {
                for (int i = 0; i < ranges.size() - 1; i++) {
                    EpisodeRange r = ranges.get(i);
                    if (lastPlayedEp >= r.start && lastPlayedEp <= r.end) {
                        activeRange = r;
                        break;
                    }
                }
            }
            if (rangeAdapter != null) {
                rangeAdapter.setRanges(ranges, activeRange);
            }
        } else {
            rvEpisodeRanges.setVisibility(View.GONE);
            activeRange = null;
        }
    }

    private void updateEpisodeDisplay() {
        List<Integer> displayList = new ArrayList<>();
        if (activeRange != null && !activeRange.isAll) {
            for (int ep : originalEpisodes) {
                if (ep >= activeRange.start && ep <= activeRange.end) {
                    displayList.add(ep);
                }
            }
        } else {
            displayList.addAll(originalEpisodes);
        }
        if (!isAscending) {
            Collections.reverse(displayList);
        }
        adapter.setEpisodes(displayList);
    }

    class EpisodeAdapter extends RecyclerView.Adapter<EpisodeAdapter.EpisodeViewHolder> {
        private final List<Integer> episodes = new ArrayList<>();
        private int cachedLastPlayedEp = -1;
        private final Set<Integer> cachedWatchedSet = new HashSet<>();

        public void setEpisodes(List<Integer> list) {
            episodes.clear();
            cachedWatchedSet.clear();
            cachedLastPlayedEp = prefs.getInt("last_ep_" + slug, -1);
            if (list != null) {
                episodes.addAll(list);
                for (int ep : list) {
                    if (prefs.getBoolean("watched_" + slug + "_" + ep, false)) {
                        cachedWatchedSet.add(ep);
                    }
                }
            }
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public EpisodeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_episode, parent, false);
            return new EpisodeViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull EpisodeViewHolder holder, int position) {
            int ep = episodes.get(position);
            holder.tvTitle.setText(String.format("EP %02d", ep));

            if (ep == cachedLastPlayedEp) {
                // Last played episode
                holder.card.setCardBackgroundColor(0xFF1C2230);
                holder.tvTitle.setTextColor(0xFF38BDF8);
                holder.tvBadge.setVisibility(View.VISIBLE);
                holder.tvBadge.setText("TERAKHIR");
                holder.tvBadge.setTextColor(0xFF38BDF8);
            } else if (cachedWatchedSet.contains(ep)) {
                // Watched episode
                holder.card.setCardBackgroundColor(0xFF0E1017);
                holder.tvTitle.setTextColor(0xFF64748B);
                holder.tvBadge.setVisibility(View.VISIBLE);
                holder.tvBadge.setText("DITONTON");
                holder.tvBadge.setTextColor(0xFF10B981);
            } else {
                // Unwatched episode
                holder.card.setCardBackgroundColor(0xFF11141C);
                holder.tvTitle.setTextColor(0xFFF1F5F9);
                holder.tvBadge.setVisibility(View.GONE);
            }

            holder.itemView.setOnClickListener(v -> playEpisode(ep));
        }

        @Override
        public int getItemCount() {
            return episodes.size();
        }

        class EpisodeViewHolder extends RecyclerView.ViewHolder {
            CardView card;
            TextView tvTitle;
            TextView tvBadge;

            public EpisodeViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_episode);
                tvTitle = itemView.findViewById(R.id.tv_ep_title);
                tvBadge = itemView.findViewById(R.id.tv_ep_status_badge);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }

    class RangeAdapter extends RecyclerView.Adapter<RangeAdapter.RangeViewHolder> {
        private final List<EpisodeRange> ranges = new ArrayList<>();
        private EpisodeRange selectedRange;

        public void setRanges(List<EpisodeRange> list, EpisodeRange selected) {
            ranges.clear();
            if (list != null) ranges.addAll(list);
            this.selectedRange = selected;
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public RangeViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_range_chip, parent, false);
            return new RangeViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull RangeViewHolder holder, int position) {
            EpisodeRange r = ranges.get(position);
            holder.tvLabel.setText(r.label);
            boolean isSel = (selectedRange != null && selectedRange.label.equals(r.label));
            if (isSel) {
                holder.card.setCardBackgroundColor(0xFF1E293B);
                holder.card.setStrokeColor(0xFF38BDF8);
                holder.tvLabel.setTextColor(0xFF38BDF8);
            } else {
                holder.card.setCardBackgroundColor(0xFF161B26);
                holder.card.setStrokeColor(0xFF2A3347);
                holder.tvLabel.setTextColor(0xFF94A3B8);
            }
            holder.itemView.setOnClickListener(v -> {
                selectedRange = r;
                activeRange = r;
                notifyDataSetChanged();
                updateEpisodeDisplay();
            });
        }

        @Override
        public int getItemCount() {
            return ranges.size();
        }

        class RangeViewHolder extends RecyclerView.ViewHolder {
            MaterialCardView card;
            TextView tvLabel;

            public RangeViewHolder(@NonNull View itemView) {
                super(itemView);
                card = itemView.findViewById(R.id.card_range_chip);
                tvLabel = itemView.findViewById(R.id.tv_range_label);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }

    private void loadRelations() {
        if (slug == null || slug.isEmpty()) return;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/anime/" + URLEncoder.encode(slug, "UTF-8") + "/relations"
                        + "?title=" + URLEncoder.encode(title != null ? title : "", "UTF-8");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(12000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONObject res = new JSONObject(sb.toString());
                if (res.optBoolean("success")) {
                    JSONArray relArr = res.getJSONObject("data").getJSONArray("relations");
                    List<JSONObject> list = new ArrayList<>();
                    for (int i = 0; i < relArr.length(); i++) {
                        JSONObject item = relArr.getJSONObject(i);
                        String itemSlug = item.optString("slug", "");
                        if (!itemSlug.isEmpty() && !itemSlug.equals(slug)) {
                            list.add(item);
                        }
                    }
                    runOnUiThread(() -> {
                        if (!list.isEmpty() && seasonAdapter != null && layoutSeasons != null) {
                            seasonAdapter.setRelations(list);
                            layoutSeasons.setVisibility(View.VISIBLE);
                        } else if (layoutSeasons != null) {
                            layoutSeasons.setVisibility(View.GONE);
                        }
                    });
                }
            } catch (Exception ignored) {
                runOnUiThread(() -> {
                    if (layoutSeasons != null) layoutSeasons.setVisibility(View.GONE);
                });
            }
        }).start();
    }

    private void loadFavoriteState() {
        if (slug == null || slug.isEmpty() || btnStarFavorite == null) return;
        new Thread(() -> {
            try {
                String u = "http://127.0.0.1:8767/api/favorites/check?slug=" + URLEncoder.encode(slug, "UTF-8");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();
                JSONObject res = new JSONObject(sb.toString());
                boolean fav = false;
                if (res.optBoolean("success")) {
                    JSONObject d = res.optJSONObject("data");
                    fav = d != null && d.optBoolean("favorite");
                }
                final boolean favFinal = fav;
                runOnUiThread(() -> {
                    isFavorite = favFinal;
                    updateStarUi();
                });
            } catch (Exception ignored) {}
        }).start();
    }

    private void toggleFavorite() {
        if (slug == null || slug.isEmpty()) return;
        final boolean target = !isFavorite;
        isFavorite = target;
        updateStarUi();
        Toast.makeText(this, target ? "Ditambahkan ke Favorit" : "Dihapus dari Favorit", Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            try {
                String base = "http://127.0.0.1:8767/api/favorites";
                String u = target ? base : base + "?slug=" + URLEncoder.encode(slug, "UTF-8");
                HttpURLConnection conn = (HttpURLConnection) new URL(u).openConnection();
                conn.setRequestMethod(target ? "POST" : "DELETE");
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);
                if (target) {
                    JSONObject b = new JSONObject();
                    b.put("slug", slug);
                    b.put("title", title != null ? title : slug);
                    b.put("poster", poster != null ? poster : "");
                    b.put("type", type != null ? type : "");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);
                    java.io.OutputStream os = conn.getOutputStream();
                    os.write(b.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                    os.close();
                }
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    private void updateStarUi() {
        if (btnStarFavorite == null) return;
        btnStarFavorite.setText(isFavorite ? "★" : "☆");
        btnStarFavorite.setTextColor(isFavorite ? 0xFFFACC15 : 0xFF64748B);
    }

    class SeasonAdapter extends RecyclerView.Adapter<SeasonAdapter.SeasonViewHolder> {
        private final List<JSONObject> relations = new ArrayList<>();

        public void setRelations(List<JSONObject> list) {
            relations.clear();
            if (list != null) relations.addAll(list);
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public SeasonViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_season_chip, parent, false);
            return new SeasonViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull SeasonViewHolder holder, int position) {
            JSONObject item = relations.get(position);
            String relType = item.optString("relation", "");
            String label = item.optString("label", "Season");
            String relTitle = item.optString("title", "");
            String relSlug = item.optString("slug", "");
            String relPoster = item.optString("poster", "");
            String relFormat = item.optString("format", "TV");

            holder.tvBadge.setText(label.toUpperCase());
            holder.tvTitle.setText(relTitle);

            if ("PREQUEL".equalsIgnoreCase(relType)) {
                holder.tvBadge.setTextColor(0xFF38BDF8); // Cyan
            } else if ("SEQUEL".equalsIgnoreCase(relType)) {
                holder.tvBadge.setTextColor(0xFFC084FC); // Purple
            } else if ("MOVIE".equalsIgnoreCase(relFormat)) {
                holder.tvBadge.setTextColor(0xFFFACC15); // Gold/Yellow
            } else {
                holder.tvBadge.setTextColor(0xFF94A3B8); // Slate
            }

            holder.itemView.setOnClickListener(v -> {
                Intent intent = new Intent(DetailActivity.this, DetailActivity.class);
                intent.putExtra("slug", relSlug);
                intent.putExtra("title", relTitle);
                intent.putExtra("poster", relPoster.isEmpty() ? poster : relPoster);
                intent.putExtra("type", relFormat);
                intent.putExtra("eps", "");
                intent.putExtra("sub", "SUB");
                startActivity(intent);
                finish();
            });
        }

        @Override
        public int getItemCount() {
            return relations.size();
        }

        class SeasonViewHolder extends RecyclerView.ViewHolder {
            TextView tvBadge;
            TextView tvTitle;

            public SeasonViewHolder(@NonNull View itemView) {
                super(itemView);
                tvBadge = itemView.findViewById(R.id.tv_season_badge);
                tvTitle = itemView.findViewById(R.id.tv_season_title);
                TvFocusHelper.attachFocusScale(itemView, 1.08f, 6f);
            }
        }
    }
}
