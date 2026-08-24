"""Unit tests for IntelligentCacheManager: shared instance, semantic hit, isolation."""
import json
import os

import pytest

from autowing.core.cache import cache_manager
from autowing.core.cache.cache_manager import (
    IntelligentCacheManager,
    get_intelligent_cache_manager,
)


@pytest.fixture
def tmp_cache_dir(tmp_path):
    return str(tmp_path / "cache")


@pytest.fixture(autouse=True)
def reset_shared_instances():
    """Ensure each test starts with a clean shared-instance registry."""
    cache_manager._reset_instances()
    yield
    cache_manager._reset_instances()


class TestSharedInstance:
    def test_same_cache_dir_returns_same_instance(self, tmp_cache_dir):
        m1 = get_intelligent_cache_manager(cache_dir=tmp_cache_dir)
        m2 = get_intelligent_cache_manager(cache_dir=tmp_cache_dir)
        assert m1 is m2

    def test_different_cache_dir_returns_different_instance(self, tmp_path):
        m1 = get_intelligent_cache_manager(cache_dir=str(tmp_path / "a"))
        m2 = get_intelligent_cache_manager(cache_dir=str(tmp_path / "b"))
        assert m1 is not m2

    def test_cache_survives_across_fixture_instantiations(self, tmp_cache_dir, monkeypatch):
        """Cache written by one fixture must be visible to a later fixture."""
        monkeypatch.setenv("AUTOWING_CACHE_DIR", tmp_cache_dir)

        from autowing.core.ai_fixture_base import AiFixtureBase

        f1 = AiFixtureBase()
        f2 = AiFixtureBase()
        # Both fixtures share the exact same manager instance
        assert f1.cache_manager is f2.cache_manager

        context = {"url": "https://example.com", "elements": []}
        f1.cache_manager.set_intelligent("click the login button", context, {"ok": 1})
        # Semantic hit through the second fixture instance
        assert f2.cache_manager.get_intelligent("click login button", context) == {"ok": 1}


class TestSemanticCache:
    def test_set_then_exact_get(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        assert manager.get_intelligent("click the login button", context) == "result-a"

    def test_semantic_hit_with_rephrased_prompt(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir, similarity_threshold=0.5)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        # Rephrased prompt, same context -> semantic hit
        assert manager.get_intelligent("click login button", context) == "result-a"

    def test_different_context_no_hit(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        ctx1 = {"url": "https://a.com", "elements": []}
        ctx2 = {"url": "https://b.com", "elements": []}
        manager.set_intelligent("click the login button", ctx1, "result-a")
        assert manager.get_intelligent("click the login button", ctx2) is None

    def test_dissimilar_prompt_no_hit(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir, similarity_threshold=0.7)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        assert manager.get_intelligent("fill the username field", context) is None

    def test_empty_cache_returns_none(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        assert manager.get_intelligent("anything", {}) is None

    def test_cache_persisted_to_disk(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        manager.set_intelligent("click button", {"url": "https://x.com"}, "ok")
        files = [f for f in os.listdir(tmp_cache_dir) if f.endswith(".json")]
        assert len(files) == 1
        with open(os.path.join(tmp_cache_dir, files[0]), encoding="utf-8") as f:
            data = json.load(f)
        assert data["prompt"] == "click button"
        assert data["response"] == "ok"

    def test_new_instance_loads_persisted_cache(self, tmp_cache_dir):
        context = {"url": "https://example.com", "elements": []}
        m1 = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        m1.set_intelligent("click the login button", context, "result-a")
        # A brand-new manager (simulating a new process) reloads from disk
        m2 = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        assert m2.get_intelligent("click the login button", context) == "result-a"


class TestContextHash:
    def test_dynamic_fields_ignored(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        ctx1 = {"url": "https://x.com", "elementMarkers": {"a": 1},
                "elements": [{"text": "登录", "autowingId": "m-1", "boundingBox": [0, 0]}]}
        ctx2 = {"url": "https://x.com", "elementMarkers": {"b": 2},
                "elements": [{"text": "登录", "autowingId": "m-999", "boundingBox": [9, 9]}]}
        assert manager._generate_context_hash(ctx1) == manager._generate_context_hash(ctx2)

    def test_real_change_alters_hash(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        ctx1 = {"url": "https://x.com"}
        ctx2 = {"url": "https://y.com"}
        assert manager._generate_context_hash(ctx1) != manager._generate_context_hash(ctx2)


class TestStatistics:
    def test_empty_statistics(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        assert manager.get_statistics()["total_entries"] == 0

    def test_usage_count_increments_on_hit(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        context = {"url": "https://example.com"}
        manager.set_intelligent("click the login button", context, "r")
        manager.get_intelligent("click the login button", context)
        stats = manager.get_statistics()
        assert stats["total_entries"] == 1
        assert stats["total_usage"] == 2  # initial 1 + one hit


class TestInvalidate:
    def test_invalidate_exact_entry(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        assert manager.invalidate("click the login button", context) is True
        # Entry gone from memory and disk
        assert manager.get_intelligent("click the login button", context) is None
        assert len(manager.cache_entries) == 0
        assert [f for f in os.listdir(tmp_cache_dir) if f.endswith(".json")] == []

    def test_invalidate_no_match_returns_false(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        assert manager.invalidate("totally unrelated prompt", {"url": "https://other.com"}) is False
        assert len(manager.cache_entries) == 1

    def test_invalidate_semantically_similar_entry(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir, similarity_threshold=0.5)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        # Rephrased prompt would hit the same entry via get_intelligent,
        # so invalidate must evict it too
        assert manager.invalidate("click login button", context) is True
        assert manager.get_intelligent("click the login button", context) is None

    def test_invalidate_keeps_other_contexts(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        ctx1 = {"url": "https://a.com", "elements": []}
        ctx2 = {"url": "https://b.com", "elements": []}
        manager.set_intelligent("click the login button", ctx1, "result-a")
        manager.set_intelligent("click the login button", ctx2, "result-b")
        assert manager.invalidate("click the login button", ctx1) is True
        # Same prompt on a different page context must survive
        assert manager.get_intelligent("click the login button", ctx2) == "result-b"

    def test_invalidate_rebuilds_index_for_remaining_entries(self, tmp_cache_dir):
        manager = IntelligentCacheManager(cache_dir=tmp_cache_dir)
        context = {"url": "https://example.com", "elements": []}
        manager.set_intelligent("click the login button", context, "result-a")
        manager.set_intelligent("fill the username field", context, "result-b")
        manager.invalidate("click the login button", context)
        # Remaining entry still queryable with a consistent vector index
        assert manager.get_intelligent("fill the username field", context) == "result-b"
