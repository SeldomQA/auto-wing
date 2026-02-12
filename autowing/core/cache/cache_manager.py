import hashlib
import json
import os
import math
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from dataclasses import dataclass
from collections import defaultdict, Counter

from loguru import logger


@dataclass
class CacheEntry:
    """Cache entry with metadata for intelligent caching"""
    key: str
    prompt: str
    context_hash: str
    response: Any
    timestamp: datetime
    similarity_score: float = 0.0
    usage_count: int = 1


class ImprovedTFIDFVectorizer:
    """Improved TF-IDF vectorizer for better semantic matching"""
    
    def __init__(self, ngram_range=(1, 2), max_features=500):
        self.ngram_range = ngram_range
        self.max_features = max_features
        self.vocabulary_ = {}
        self.idf_ = {}
        self.vocab_size = 0
        self.doc_freq_ = defaultdict(int)
        
    def _preprocess_text(self, text: str) -> str:
        """Text preprocessing"""
        # Convert to lowercase and remove common stop word patterns
        text = text.lower()
        # Simple stop word handling
        stop_patterns = ['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个']
        for pattern in stop_patterns:
            text = text.replace(pattern, '')
        return text.strip()
    
    def _generate_ngrams(self, text: str, n: int) -> List[str]:
        """Generate n-grams, supporting both Chinese and English"""
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Handle mixed Chinese and English text
        tokens = []
        i = 0
        while i < len(processed_text):
            # Check if it's a Chinese character
            if '\u4e00' <= processed_text[i] <= '\u9fff':
                tokens.append(processed_text[i])
                i += 1
            else:
                # English word processing
                if processed_text[i].isalnum():
                    word_start = i
                    while i < len(processed_text) and (processed_text[i].isalnum() or processed_text[i] == "'"):
                        i += 1
                    if i > word_start:
                        tokens.append(processed_text[word_start:i])
                else:
                    i += 1
        
        # Generate n-grams
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ''.join(tokens[i:i + n]) if any('\u4e00' <= c <= '\u9fff' for c in ''.join(tokens[i:i + n])) else ' '.join(tokens[i:i + n])
            if ngram.strip():
                ngrams.append(ngram)
        return ngrams
    
    def _get_all_ngrams(self, texts: List[str]) -> List[str]:
        """Get all n-grams from texts"""
        all_ngrams = []
        for text in texts:
            for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
                all_ngrams.extend(self._generate_ngrams(text, n))
        return all_ngrams
    
    def fit_transform(self, texts: List[str]):
        """Fit and transform texts"""
        if not texts:
            return []
            
        # Count document frequencies
        self.doc_freq_ = defaultdict(int)
        all_ngrams_list = []
        
        for text in texts:
            text_ngrams = []
            for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
                text_ngrams.extend(self._generate_ngrams(text, n))
            all_ngrams_list.append(text_ngrams)
            
            # Count how many documents each n-gram appears in
            unique_ngrams = set(text_ngrams)
            for ngram in unique_ngrams:
                self.doc_freq_[ngram] += 1
        
        # Build vocabulary (select most frequent n-grams)
        sorted_ngrams = sorted(self.doc_freq_.items(), key=lambda x: x[1], reverse=True)
        selected_ngrams = [ngram for ngram, freq in sorted_ngrams[:self.max_features]]
        
        # Build vocabulary mapping
        self.vocabulary_ = {ngram: idx for idx, ngram in enumerate(selected_ngrams)}
        self.vocab_size = len(self.vocabulary_)
        
        # Calculate IDF values
        doc_count = len(texts)
        self.idf_ = {}
        for ngram in self.vocabulary_:
            df = self.doc_freq_[ngram]
            # Use smoothed IDF formula
            self.idf_[ngram] = math.log((doc_count + 1) / (df + 1)) + 1
        
        # Transform to vectors
        return self.transform(texts)
    
    def transform(self, texts: List[str]):
        """Transform texts to vectors"""
        vectors = []
        for text in texts:
            vector = [0.0] * self.vocab_size
            
            # Generate all n-grams for current text
            text_ngrams = []
            for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
                text_ngrams.extend(self._generate_ngrams(text, n))
            
            if not text_ngrams:
                vectors.append(vector)
                continue
            
            # Calculate TF (term frequency)
            tf_counter = Counter(text_ngrams)
            total_terms = len(text_ngrams)
            
            # Calculate TF-IDF
            for ngram, count in tf_counter.items():
                if ngram in self.vocabulary_:
                    idx = self.vocabulary_[ngram]
                    # Use logarithmic TF scaling
                    tf_value = 1 + math.log(count) if count > 0 else 0
                    vector[idx] = tf_value * self.idf_[ngram]
            
            vectors.append(vector)
        
        return vectors


class IntelligentCacheManager:
    """
    Intelligent cache manager that uses semantic similarity to find cache hits
    even when exact matches don't exist.
    """

    def __init__(self, cache_dir: str = ".auto-wing/cache", ttl_days: int = 7, 
                 similarity_threshold: float = 0.7):
        """
        Initialize the intelligent cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_days: Number of days to keep cache entries
            similarity_threshold: Minimum similarity score for cache hit (0.0-1.0)
        """
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        self.similarity_threshold = similarity_threshold
        self.vectorizer = ImprovedTFIDFVectorizer(ngram_range=(1, 2), max_features=500)
        os.makedirs(cache_dir, exist_ok=True)
        self._load_existing_cache()

    def _load_existing_cache(self):
        """Load existing cache entries and build similarity index"""
        self.cache_entries: List[CacheEntry] = []
        self.prompt_vectors = []
        
        # Load all existing cache files
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cache_data['timestamp'])
                # Skip expired entries
                if datetime.now() - cached_time > timedelta(days=self.ttl_days):
                    os.remove(filepath)
                    continue
                
                # Create cache entry
                entry = CacheEntry(
                    key=filename.replace('.json', ''),
                    prompt=cache_data['prompt'],
                    context_hash=self._generate_context_hash(cache_data.get('context', {})),
                    response=cache_data['response'],
                    timestamp=cached_time
                )
                
                self.cache_entries.append(entry)
                
            except (json.JSONDecodeError, KeyError, ValueError):
                # Remove invalid cache files
                os.remove(filepath)
        
        # Build TF-IDF vectors for all prompts
        if self.cache_entries:
            prompts = [entry.prompt for entry in self.cache_entries]
            self.prompt_vectors = self.vectorizer.fit_transform(prompts)

    def _generate_context_hash(self, context: dict) -> str:
        """Generate a stable hash for context that ignores dynamic elements"""
        # Remove dynamic fields that change between executions
        stable_context = {}
        if isinstance(context, dict):
            for key, value in context.items():
                # Skip dynamic fields
                if key in ['elementMarkers', 'autowingId']:
                    continue
                if key == 'elements' and isinstance(value, list):
                    # Process elements to remove dynamic IDs
                    stable_elements = []
                    for element in value:
                        if isinstance(element, dict):
                            stable_element = {
                                k: v for k, v in element.items() 
                                if k not in ['autowingId', 'boundingBox']
                            }
                            stable_elements.append(stable_element)
                    stable_context[key] = stable_elements
                else:
                    stable_context[key] = value
        
        return hashlib.md5(
            json.dumps(stable_context, sort_keys=True).encode()
        ).hexdigest()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Calculate vector magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def _calculate_similarity(self, prompt1: str, prompt2: str) -> float:
        """Calculate semantic similarity between two prompts"""
        if not self.prompt_vectors or not self.cache_entries:
            return 0.0
            
        # Transform both prompts
        vectors = self.vectorizer.transform([prompt1, prompt2])
        if len(vectors) < 2:
            return 0.0
            
        vec1, vec2 = vectors[0], vectors[1]
        return self._cosine_similarity(vec1, vec2)

    def get_intelligent(self, prompt: str, context: dict) -> Optional[Any]:
        """
        Get cached response using intelligent matching based on semantic similarity.
        
        Args:
            prompt: The prompt to search for
            context: Current context to match against
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self.cache_entries:
            return None
            
        current_context_hash = self._generate_context_hash(context)
        best_match: Optional[CacheEntry] = None
        best_similarity = 0.0
        
        # Search for best matching entry
        for entry in self.cache_entries:
            # First check if context is compatible
            if entry.context_hash != current_context_hash:
                continue
                
            # Calculate semantic similarity
            similarity = self._calculate_similarity(prompt, entry.prompt)
            
            # Update best match if this is better
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = entry
        
        if best_match:
            best_match.similarity_score = best_similarity
            best_match.usage_count += 1
            logger.debug(f"🧠 Intelligent cache hit (similarity: {best_similarity:.2f}): {prompt}")
            return best_match.response
            
        return None

    def set_intelligent(self, prompt: str, context: dict, response: Any) -> None:
        """
        Store response in intelligent cache.
        
        Args:
            prompt: The prompt used
            context: Context information
            response: The response to cache
        """
        # Generate cache key
        cache_key = hashlib.md5(f"{prompt}:{self._generate_context_hash(context)}".encode()).hexdigest()
        
        # Create new cache entry
        new_entry = CacheEntry(
            key=cache_key,
            prompt=prompt,
            context_hash=self._generate_context_hash(context),
            response=response,
            timestamp=datetime.now()
        )
        
        # Add to cache entries
        self.cache_entries.append(new_entry)
        
        # Update vectorizer with new prompt
        prompts = [entry.prompt for entry in self.cache_entries]
        self.prompt_vectors = self.vectorizer.fit_transform(prompts)
        
        # Save to file
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        cache_data = {
            'timestamp': new_entry.timestamp.isoformat(),
            'prompt': prompt,
            'context': context,
            'response': response
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"💾 Intelligent cache saved: {prompt}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache_entries)
        if total_entries == 0:
            return {"total_entries": 0, "hit_rate": 0.0}
            
        total_usage = sum(entry.usage_count for entry in self.cache_entries)
        avg_similarity = sum(entry.similarity_score for entry in self.cache_entries if entry.similarity_score > 0) / max(1, sum(1 for entry in self.cache_entries if entry.similarity_score > 0))
        
        return {
            "total_entries": total_entries,
            "total_usage": total_usage,
            "average_similarity": avg_similarity,
            "hit_rate": total_usage / total_entries if total_entries > 0 else 0.0
        }

    def clear_expired(self) -> None:
        """Remove expired cache entries"""
        current_time = datetime.now()
        expired_entries = []
        
        for entry in self.cache_entries:
            if current_time - entry.timestamp > timedelta(days=self.ttl_days):
                expired_entries.append(entry)
                # Remove file
                cache_path = os.path.join(self.cache_dir, f"{entry.key}.json")
                if os.path.exists(cache_path):
                    os.remove(cache_path)
        
        # Remove expired entries from memory
        for entry in expired_entries:
            self.cache_entries.remove(entry)
        
        # Rebuild vectors
        if self.cache_entries:
            prompts = [entry.prompt for entry in self.cache_entries]
            self.prompt_vectors = self.vectorizer.fit_transform(prompts)
