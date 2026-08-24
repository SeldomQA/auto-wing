"""Unit tests for the self-implemented TF-IDF vectorizer (ImprovedTFIDFVectorizer)."""
import pytest

from autowing.core.cache.cache_manager import ImprovedTFIDFVectorizer


@pytest.fixture
def vectorizer():
    return ImprovedTFIDFVectorizer(ngram_range=(1, 2), max_features=500)


class TestPreprocess:
    def test_lowercase(self, vectorizer):
        assert vectorizer._preprocess_text("Click BUTTON") == "click button"

    def test_stop_words_removed(self, vectorizer):
        # Chinese stop words like 的/了/在 should be stripped
        processed = vectorizer._preprocess_text("我的按钮在哪里了")
        assert "的" not in processed
        assert "了" not in processed


class TestNgrams:
    def test_chinese_unigrams(self, vectorizer):
        ngrams = vectorizer._generate_ngrams("点击按钮", n=1)
        assert "点" in ngrams and "击" in ngrams

    def test_english_words(self, vectorizer):
        ngrams = vectorizer._generate_ngrams("click the button", n=1)
        assert "click" in ngrams and "button" in ngrams

    def test_english_bigram_joined_by_space(self, vectorizer):
        ngrams = vectorizer._generate_ngrams("click button", n=2)
        assert "click button" in ngrams

    def test_mixed_chinese_english(self, vectorizer):
        # Current tokenizer behavior: CJK characters pass isalnum(), so an
        # ASCII word glued to CJK text forms a single mixed token (e.g.
        # 'login按钮'). Recorded as-is; splitting on script boundaries is a
        # possible future improvement.
        ngrams = vectorizer._generate_ngrams("点击login按钮", n=1)
        assert "点" in ngrams and "击" in ngrams
        assert "login按钮" in ngrams

    def test_empty_text(self, vectorizer):
        assert vectorizer._generate_ngrams("", n=1) == []


class TestFitTransform:
    def test_empty_input(self, vectorizer):
        assert vectorizer.fit_transform([]) == []

    def test_vector_shape(self, vectorizer):
        texts = ["click the login button", "click the submit button"]
        vectors = vectorizer.fit_transform(texts)
        assert len(vectors) == 2
        assert all(len(v) == vectorizer.vocab_size for v in vectors)

    def test_identical_texts_similarity_one(self, vectorizer):
        vectors = vectorizer.fit_transform(["click button", "click button"])
        # Identical non-zero vectors must have cosine similarity 1.0
        dot = sum(a * b for a, b in zip(vectors[0], vectors[1]))
        norm = (sum(a * a for a in vectors[0]) ** 0.5) * (sum(b * b for b in vectors[1]) ** 0.5)
        assert dot / norm == pytest.approx(1.0)

    def test_different_texts_lower_similarity(self, vectorizer):
        texts = ["click the login button", "fill the username field"]
        vectors = vectorizer.fit_transform(texts)
        dot = sum(a * b for a, b in zip(vectors[0], vectors[1]))
        norm = (sum(a * a for a in vectors[0]) ** 0.5) * (sum(b * b for b in vectors[1]) ** 0.5)
        similarity = dot / norm if norm else 0.0
        assert similarity < 1.0

    def test_max_features_limits_vocabulary(self):
        vectorizer = ImprovedTFIDFVectorizer(ngram_range=(1, 2), max_features=3)
        texts = ["alpha beta gamma delta", "epsilon zeta eta theta"]
        vectorizer.fit_transform(texts)
        assert vectorizer.vocab_size <= 3

    def test_transform_unseen_text_returns_zero_for_unknown_terms(self, vectorizer):
        vectorizer.fit_transform(["click button"])
        vectors = vectorizer.transform(["completely different words here"])
        assert len(vectors) == 1
        assert all(v == 0.0 for v in vectors[0])

    def test_idf_higher_for_rare_terms(self, vectorizer):
        # 'shared' appears in both documents, 'unique1' only in the first one
        texts = ["shared unique1", "shared unique2"]
        vectorizer.fit_transform(texts)
        assert vectorizer.idf_["unique1"] > vectorizer.idf_["shared"]
