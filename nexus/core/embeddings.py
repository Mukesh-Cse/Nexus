"""Cached sentence embeddings when explicitly enabled, TF-IDF cosine fallback otherwise."""
import os
from functools import lru_cache
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@lru_cache(maxsize=1)
def sentence_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(os.getenv("NEXUS_EMBEDDING_MODEL","all-MiniLM-L6-v2"), local_files_only=True)

@lru_cache(maxsize=2048)
def _sentence(text):
    return tuple(float(v) for v in sentence_model().encode(text, normalize_embeddings=True))

def similarity(a, b):
    if not a.strip() or not b.strip():
        return 0.0
    if os.getenv("NEXUS_EMBEDDINGS","tfidf") == "sentence":
        try:
            return round(max(0.,float(np.dot(_sentence(a),_sentence(b)))) * 100,2)
        except (ImportError,OSError,RuntimeError):
            pass
    try:
        x = TfidfVectorizer(ngram_range=(1,2),strip_accents="unicode").fit_transform([a,b])
        return round(float(cosine_similarity(x[0],x[1])[0,0])*100,2)
    except ValueError:
        return 0.0

def backend():
    if os.getenv("NEXUS_EMBEDDINGS") == "sentence":
        try:
            sentence_model()
            return "Sentence Transformers (local model)"
        except (ImportError,OSError,RuntimeError):
            return "TF-IDF cosine · sentence model unavailable"
    return "TF-IDF cosine (offline fallback)"

