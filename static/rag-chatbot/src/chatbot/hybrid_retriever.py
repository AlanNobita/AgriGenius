import os
import json
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .embeddings import Embeddings


BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(BASE_DIR, "data")
PDFS_DIR = os.path.join(DATA_DIR, "pdfs")
INDICES_DIR = os.path.join(DATA_DIR, "indices")
DOC_STORE = os.path.join(INDICES_DIR, "documents.json")

os.makedirs(PDFS_DIR, exist_ok=True)
os.makedirs(INDICES_DIR, exist_ok=True)


class HybridRetriever:
    """Persistent hybrid retriever using TF-IDF + semantic embeddings.

    Documents are stored as list of dicts: {id, text, meta}
    """

    def __init__(self):
        self.documents: List[dict] = []
        self.tfidf = None
        self.tfidf_matrix = None
        self.embeddings = None
        self.embedder = Embeddings()
        self._load()

    def _load(self):
        if os.path.exists(DOC_STORE):
            try:
                with open(DOC_STORE, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []
        else:
            self.documents = []

        if self.documents:
            texts = [d["text"] for d in self.documents]
            if texts:  # Only embed if we have texts
                try:
                    # Check if embedding model is available first
                    from .embeddings import check_embedding_model_available
                    if not check_embedding_model_available():
                        print("Warning: Embedding model not available, using fallback embeddings")
                    
                    self.embeddings = self.embedder.embed(texts, batch_size=16)
                    print(f"Successfully embedded {len(texts)} documents with shape: {self.embeddings.shape}")
                except Exception as e:
                    print(f"Embedding failed: {e}")
                    self.embeddings = np.zeros((len(texts), 256))  # Fallback size
                self._rebuild_tfidf(texts)
            else:
                self.embeddings = np.zeros((0, 256))
        else:
            self.embeddings = np.zeros((0, 256))

    def _save(self):
        with open(DOC_STORE, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

    def _rebuild_tfidf(self, texts: List[str]):
        self.tfidf = TfidfVectorizer().fit(texts)
        self.tfidf_matrix = self.tfidf.transform(texts)

    def add_documents(self, docs: List[dict]):
        self.documents.extend(docs)
        texts = [d["text"] for d in self.documents]
        try:
            # Check if embedding model is available first
            from .embeddings import check_embedding_model_available
            if not check_embedding_model_available():
                print("Warning: Embedding model not available, using fallback embeddings")
            
            self.embeddings = self.embedder.embed(texts, batch_size=16)
            print(f"Successfully embedded {len(texts)} documents with shape: {self.embeddings.shape}")
        except Exception as e:
            print(f"Embedding failed during document addition: {e}")
            self.embeddings = np.zeros((len(texts), 256))  # Fallback size
        self._rebuild_tfidf(texts)
        self._save()

    def semantic_scores(self, query: str, top_k: int = 5):
        try:
            if self.embeddings is None or self.embeddings.size == 0:
                print("No embeddings available for semantic search")
                return []
            if not self.documents:
                print("No documents available for semantic search")
                return []
                
            q_emb = self.embedder.embed([query])[0]
            qn = q_emb / (np.linalg.norm(q_emb) + 1e-12)
            en = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-12)
            sims = (en @ qn).astype(float)
            idx = np.argsort(-sims)[:top_k]
            results = []
            for i in idx:
                if i < len(self.documents):  # Safety check
                    results.append({"doc": self.documents[i], "score": float(sims[i])})
            print(f"Semantic search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"Semantic search failed: {e}")
            return []

    def lexical_scores(self, query: str, top_k: int = 5):
        try:
            if self.tfidf is None:
                print("No TF-IDF vectorizer available for lexical search")
                return []
            if not self.documents:
                print("No documents available for lexical search")
                return []
                
            q_vec = self.tfidf.transform([query])
            sims = (self.tfidf_matrix @ q_vec.T).toarray().squeeze()
            idx = np.argsort(-sims)[:top_k]
            results = []
            for i in idx:
                if i < len(self.documents):  # Safety check
                    results.append({"doc": self.documents[i], "score": float(sims[i])})
            print(f"Lexical search returned {len(results)} results")
            return results
        except Exception as e:
            print(f"Lexical search failed: {e}")
            return []

    def hybrid_search(self, query: str, top_k: int = 5, alpha: float = 0.6):
        try:
            print(f"Performing hybrid search for: '{query}' with top_k={top_k}")
            sem = self.semantic_scores(query, top_k=top_k * 2)
            lex = self.lexical_scores(query, top_k=top_k * 2)
            
            if not sem and not lex:
                print("No results from semantic or lexical search")
                return []
                
            scores = {}
            for r in sem:
                docid = r["doc"]["id"]
                scores[docid] = {"doc": r["doc"], "sem": r["score"], "lex": 0.0}
            for r in lex:
                docid = r["doc"]["id"]
                if docid not in scores:
                    scores[docid] = {"doc": r["doc"], "sem": 0.0, "lex": r["score"]}
                else:
                    scores[docid]["lex"] = r["score"]
            combined = []
            for v in scores.values():
                combined_score = alpha * v["sem"] + (1 - alpha) * v["lex"]
                combined.append({"doc": v["doc"], "score": combined_score})
            combined_sorted = sorted(combined, key=lambda x: -x["score"])
            result = combined_sorted[:top_k]
            print(f"Hybrid search returned {len(result)} results")
            return result
        except Exception as e:
            print(f"Hybrid search failed: {e}")
            return []


# module-level singleton retriever
_retriever = None


def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever