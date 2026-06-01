from pathlib import Path

from olx_imoveis.cache import CacheStore


def test_cache_ttl(tmp_path: Path):
    db = tmp_path / "test.db"
    cache = CacheStore(db)
    cache.set("k1", "valor", ttl_seconds=3600)
    assert cache.get("k1") == "valor"
    cache.set_json("k2", {"a": 1}, ttl_seconds=3600)
    assert cache.get_json("k2") == {"a": 1}
