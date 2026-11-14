"""Satu-satunya pintu validasi SSRF untuk URL eksternal yang dipakai Tatap.

Dipakai oleh `main.py` (proxy video/subtitle, play-mpv) dan `api/desync.py`
(validasi setiap hop redirect). Semua tempat lain WAJIB memanggil fungsi di
sini, jangan menduplikasi logika pengecekan host.
"""

import ipaddress
import socket
import time
import urllib.parse

_OK_TTL = 60.0
_OK_CACHE_MAX = 512
_OK_CACHE: dict = {}          # host -> expiry (monotonic)


class UnsafeURL(ValueError):
    """URL menuju host lokal/privat ditolak (SSRF protection)."""


def _is_bad_ip(ip) -> bool:
    """True untuk IP yang tidak boleh diakses dari proxy.

    IPv4-mapped IPv6 (::ffff:127.0.0.1) dinormalisasi dulu supaya tidak lolos
    sebagai "IPv6 publik".
    """
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_public_url(url: str) -> None:
    """Lempar UnsafeURL bila URL bukan http(s) publik.

    Domain yang gagal di-resolve dibiarkan lewat (perilaku lama): request-nya
    akan gagal sendiri di layer HTTP.
    """
    p = urllib.parse.urlsplit((url or "").strip())
    if p.scheme.lower() not in ("http", "https"):
        raise UnsafeURL("skema hanya http/https")
    host = (p.hostname or "").strip().lower()
    if not host:
        raise UnsafeURL("hostname kosong")
    if host in ("localhost", "0.0.0.0") or host.endswith((".local", ".internal", ".localhost")):
        raise UnsafeURL("host lokal")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if _is_bad_ip(ip):
            raise UnsafeURL("IP privat/lokal")
        return

    if _OK_CACHE.get(host, 0.0) > time.monotonic():
        return

    try:
        infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except (socket.gaierror, socket.herror):
        return

    for info in infos:
        sockaddr = info[4]
        try:
            ip = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if not _is_bad_ip(ip):
            continue
        # ISP DNS poisoning: domain publik di-resolve ke IP sinkhole privat.
        # Verifikasi ulang via DoH; kalau DoH memberi IP publik asli, izinkan.
        try:
            from api.desync import _resolve_host

            real_ip = _resolve_host(host)
            if real_ip and real_ip != host:
                rip = ipaddress.ip_address(real_ip)
                if not _is_bad_ip(rip):
                    continue
        except Exception:
            pass
        raise UnsafeURL(f"domain mengarah ke IP privat ({sockaddr[0]})")

    if len(_OK_CACHE) >= _OK_CACHE_MAX:
        _OK_CACHE.clear()
    _OK_CACHE[host] = time.monotonic() + _OK_TTL


async def httpx_request_hook(request) -> None:
    """Event hook httpx: validasi SETIAP request, termasuk hop redirect.

    Dipasang di AsyncClient yang mengambil URL dari user. Karena httpx
    memanggil hook per hop (terverifikasi di httpx 0.28), redirect dari domain
    publik ke 127.0.0.1 tidak bisa lagi melewati guard.
    """
    import asyncio

    await asyncio.to_thread(assert_public_url, str(request.url))
