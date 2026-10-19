"""Client ringan AniSkip API (v2) untuk deteksi opening (OP) dan ending (ED).

API: https://api.aniskip.com/v2/skip-times/{mal_id}/{episode_num}?types=op&types=ed&episodeLength=0
Dokumentasi & Schema:
- results: list of { skipType: 'op'|'ed'|'mixed-op'|'mixed-ed', interval: { startTime, endTime } }
"""
import time
import httpx

_CACHE = {}  # (mal_id, ep): (data, timestamp)
_CACHE_TTL = 86400  # 24 jam


def get_skip_times(mal_id, episode_num: int, timeout: float = 4.0) -> dict:
    """Mengambil interval opening dan ending dari AniSkip API.

    Returns:
        dict dengan key 'intro' dan 'outro', masing-masing memiliki 'start' dan 'end' (detik float/int).
    """
    empty_result = {
        "intro": {"start": 0, "end": 0},
        "outro": {"start": 0, "end": 0}
    }
    if not mal_id or not episode_num:
        return empty_result

    try:
        mal_int = int(str(mal_id).strip())
        ep_int = int(str(episode_num).strip())
    except Exception:
        return empty_result

    cache_key = (mal_int, ep_int)
    now = time.time()
    if cache_key in _CACHE:
        entry, ts = _CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return entry

    url = f"https://api.aniskip.com/v2/skip-times/{mal_int}/{ep_int}?types=op&types=ed&types=mixed-op&types=mixed-ed&episodeLength=0"
    headers = {
        "User-Agent": "Tatap/2.5.0 (https://github.com/asfaraguest/tatap)",
        "Accept": "application/json"
    }

    intro = {"start": 0, "end": 0}
    outro = {"start": 0, "end": 0}

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("found") and isinstance(body.get("results"), list):
                    for item in body["results"]:
                        st = (item.get("skipType") or "").lower()
                        interval = item.get("interval") or {}
                        start = round(float(interval.get("startTime") or 0), 2)
                        end = round(float(interval.get("endTime") or 0), 2)
                        if end > start:
                            if "op" in st and intro["end"] == 0:
                                intro = {"start": start, "end": end}
                            elif "ed" in st and outro["end"] == 0:
                                outro = {"start": start, "end": end}
    except Exception:
        # Graceful fallback: jaringan offline, timeout, atau AniSkip down
        pass

    res = {"intro": intro, "outro": outro}
    _CACHE[cache_key] = (res, now)
    return res
