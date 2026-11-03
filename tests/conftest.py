"""Shared pytest fixtures.

aiosqlite membuka worker thread non-daemon per koneksi. Pool koneksi backend
menyimpan koneksi hidup sampai proses berakhir — tanpa penutupan eksplisit,
interpreter hang di `threading._shutdown()` karena menunggu thread worker yang
blocked di queue selamanya.

Catatan: test mengimpor modul database dengan dua gaya (top-level `database`
via sys.path insert, dan `backend.database` sebagai package) — keduanya bisa
punya instance pool sendiri, jadi tutup semua yang ada.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session", autouse=True)
def _close_aiosqlite_pools():
    yield
    for name in ("database", "backend.database"):
        mod = sys.modules.get(name)
        if mod is None or not hasattr(mod, "close_db_pool"):
            continue
        try:
            asyncio.run(mod.close_db_pool())
        except Exception:
            # Jangan gagalkan sesi hanya karena cleanup pool.
            pass
